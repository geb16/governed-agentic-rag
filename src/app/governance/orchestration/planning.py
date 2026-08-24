"""Coordinate stages one through five without executing a proposed action.

Each stage checkpoints state and its audit event within one transaction. Deterministic
input-security blocks skip retrieval and proposal generation, then continue into risk
and routing so denial remains explicit and traceable.
"""

from collections.abc import Callable
from typing import TypeVar

from app.audit.schemas import AuditActorType, AuditEventType
from app.governance.contracts import WorkflowStage, WorkflowState
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.errors import StageExecutionError
from app.governance.orchestration.events import AuditRecorder
from app.governance.orchestration.state import WorkflowStateService
from app.governance.security import IdentityService

_ResultT = TypeVar("_ResultT")


class PlanningRunner:
    """Run and persist stages one through five without executing an action.

    Args:
        runtime: Injected stage, persistence, audit, and transaction ports.
        states: Workflow state checkpoint service.
        events: Stable audit event recorder.
        identity: Service producing pseudonymous provider safety identities.
    """

    def __init__(
        self,
        runtime: WorkflowRuntime,
        states: WorkflowStateService,
        events: AuditRecorder,
        identity: IdentityService,
    ) -> None:
        """Initialize stages one through five from explicit runtime services."""
        self._runtime = runtime
        self._states = states
        self._events = events
        self._identity = identity

    def run(
        self,
        state: WorkflowState,
        *,
        security_category: str | None,
    ) -> WorkflowState:
        """Advance a workflow through classification, evidence, risk, and routing.

        Args:
            state: Newly running workflow state.
            security_category: Deterministic input-guardrail finding, when blocked.

        Returns:
            Workflow checkpointed at approval routing.

        Raises:
            StageExecutionError: If any planning stage fails unexpectedly.
        """
        state = self._run_stage(
            WorkflowStage.TASK_CLASSIFICATION,
            state,
            lambda: self._classify(state, security_category),
        )
        if security_category:
            self._events.stage_skipped(
                state,
                WorkflowStage.KNOWLEDGE_RETRIEVAL,
                "security_input_blocked",
            )
            self._events.stage_skipped(
                state,
                WorkflowStage.PROPOSED_ACTION_GENERATION,
                "security_input_blocked",
            )
        else:
            state = self._run_stage(
                WorkflowStage.KNOWLEDGE_RETRIEVAL,
                state,
                lambda: self._retrieve(state),
            )
            state = self._run_stage(
                WorkflowStage.PROPOSED_ACTION_GENERATION,
                state,
                lambda: self._propose(state),
            )
        state = self._run_stage(
            WorkflowStage.RISK_CHECKING,
            state,
            lambda: self._check_risk(state),
        )
        return self._run_stage(
            WorkflowStage.APPROVAL_ROUTING,
            state,
            lambda: self._route_approval(state),
        )

    @staticmethod
    def _run_stage(
        stage: WorkflowStage,
        state: WorkflowState,
        operation: Callable[[], _ResultT],
    ) -> _ResultT:
        """Wrap a stage failure with its stable audit identity and prior state."""
        try:
            return operation()
        except StageExecutionError:
            raise
        except Exception as exc:
            raise StageExecutionError(stage, exc, state) from exc

    def _classify(
        self,
        state: WorkflowState,
        security_category: str | None,
    ) -> WorkflowState:
        """Run and atomically checkpoint stage-one structured classification."""
        stage = WorkflowStage.TASK_CLASSIFICATION
        self._events.stage_started(state, stage)
        result = self._runtime.classification.run(
            state.request,
            safety_identifier=self._identity.pseudonym(state.request.requester_id),
            security_category=security_category,
        )
        candidate = state.model_copy(
            update={
                "classification": result.output,
                "usage": self._states.add_usage(
                    state.usage,
                    result.input_tokens,
                    result.output_tokens,
                ),
            }
        )
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(candidate, stage)
            self._events.stage_completed(
                state,
                stage,
                result.output,
                {
                    "intent": result.output.intent.value,
                    "task_type": result.output.task_type.value,
                    "sensitivity": result.output.sensitivity.value,
                    "confidence": result.output.confidence,
                },
                actor=AuditActorType.SYSTEM if security_category else AuditActorType.MODEL,
            )
        return state

    def _retrieve(self, state: WorkflowState) -> WorkflowState:
        """Run and atomically checkpoint stage-two evidence retrieval."""
        stage = WorkflowStage.KNOWLEDGE_RETRIEVAL
        if state.classification is None:
            raise RuntimeError("Classification is required before retrieval")
        self._events.stage_started(state, stage)
        result = self._runtime.retrieval.run(state.request, state.classification)
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(
                state.model_copy(update={"retrieval": result}),
                stage,
            )
            self._events.stage_completed(
                state,
                stage,
                result,
                {
                    "route": result.route,
                    "result_count": len(result.chunks),
                    "evidence_ids": [item.evidence_id for item in result.evidence],
                },
            )
        return state

    def _propose(self, state: WorkflowState) -> WorkflowState:
        """Run and atomically checkpoint stage-three validated proposal data."""
        stage = WorkflowStage.PROPOSED_ACTION_GENERATION
        if state.classification is None or state.retrieval is None:
            raise RuntimeError("Classification and retrieval are required before proposal")
        self._events.stage_started(state, stage)
        result = self._runtime.proposal.run(
            state.request,
            state.classification,
            state.retrieval,
            safety_identifier=self._identity.pseudonym(state.request.requester_id),
        )
        candidate = state.model_copy(
            update={
                "proposal": result.output,
                "usage": self._states.add_usage(
                    state.usage,
                    result.input_tokens,
                    result.output_tokens,
                ),
            }
        )
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(candidate, stage)
            self._events.stage_completed(
                state,
                stage,
                result.output,
                {
                    "kind": result.output.kind.value,
                    "tool_name": result.output.tool_name,
                    "validation_error": result.output.validation_error,
                },
                actor=AuditActorType.MODEL,
            )
        return state

    def _check_risk(self, state: WorkflowState) -> WorkflowState:
        """Run and atomically checkpoint stage-four deterministic risk policy."""
        stage = WorkflowStage.RISK_CHECKING
        if state.classification is None:
            raise RuntimeError("Classification is required before risk checking")
        self._events.stage_started(state, stage)
        result = self._runtime.risk.run(state.classification, state.proposal)
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(
                state.model_copy(update={"risk": result}),
                stage,
            )
            self._events.stage_completed(
                state,
                stage,
                result,
                {
                    "level": result.level.value,
                    "score": result.score,
                    "flags": [flag.code for flag in result.flags],
                    "required_roles": result.required_roles,
                    "policy_version": result.policy_version,
                },
            )
        return state

    def _route_approval(self, state: WorkflowState) -> WorkflowState:
        """Run and atomically checkpoint the stage-five routing decision."""
        stage = WorkflowStage.APPROVAL_ROUTING
        if state.risk is None:
            raise RuntimeError("Risk assessment is required before approval routing")
        self._events.stage_started(state, stage)
        result = self._runtime.approval.run(state.risk, state.proposal)
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(
                state.model_copy(update={"approval_route": result}),
                stage,
            )
            self._events.stage_completed(
                state,
                stage,
                result,
                {
                    "decision": result.decision.value,
                    "required_roles": result.required_roles,
                    "proposal_digest": result.proposal_digest,
                },
                event_type=AuditEventType.DECISION_RECORDED,
            )
        return state
