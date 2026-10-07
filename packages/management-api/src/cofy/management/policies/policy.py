"""Policies: who may do what, kept apart from the endpoints doing it.

Every route is registered through a `PolicyRouter` and names the rule it is guarded by, so a route nobody thought
about authorizing can't exist: leaving the rule out fails when the router is built. One policy covers every subject
alike; a subclass of it handles a subject whose rules differ.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import Enum
from typing import Annotated, Any, Final, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.params import Depends as DependsParam

from ..auth.access import Action, Subject
from ..auth.user import User, current_user
from ..errors import ForbiddenError


class Policy:
    """The rules for a subject, named after the router methods they guard.

    Seeing the subject takes `read` on it and changing it `write`, in the community the route is about, or outside any
    one community on a route without a slug.
    """

    def __init__(self, user: User, request: Request, subject: Subject | None):
        self.user = user
        self.request = request
        self.subject = subject
        self.slug: str | None = request.path_params.get("slug")

    def allows(self, rule: Rule) -> bool:
        """Whether *rule* lets the user through; a system admin may do anything, whatever the rule says."""
        return self.user.system_admin or rule(self)

    def can(self, action: Action) -> bool:
        """Whether the user may do *action* to the subject, in the route's community."""
        if self.subject is None:
            raise ValueError("A rule about a subject is guarding a route whose router has none")
        return self.user.can(action, self.subject, self.slug)

    def authenticated(self) -> bool:
        """Anyone logged in."""
        return True

    def all(self) -> bool:
        return self.can(Action.read)

    def get(self) -> bool:
        return self.can(Action.read)

    def create(self) -> bool:
        return self.can(Action.write)

    def put(self) -> bool:
        return self.can(Action.write)

    def delete(self) -> bool:
        return self.can(Action.write)


Rule = Callable[[Any], bool]
"""A policy's rule, as its unbound method: `Policy.put`."""


class _Public(Enum):
    PUBLIC = "public"


PUBLIC: Final = _Public.PUBLIC
"""The rule for a route anyone may use, logged in or not."""


class PolicyCheck:
    """The dependency guarding a route, which every route has exactly one of."""


class RuleCheck(PolicyCheck):
    """Checks the request's user against one rule of a policy."""

    def __init__(self, policy: type[Policy], subject: Subject | None, rule: Rule):
        self.policy = policy
        self.subject = subject
        self.rule = rule

    def __call__(self, request: Request, user: Annotated[User, Depends(current_user)]) -> None:
        if not self.policy(user, request, self.subject).allows(self.rule):
            raise ForbiddenError("You are not allowed to do this")


class PublicCheck(PolicyCheck):
    """Lets anyone through, without needing a login."""

    def __call__(self) -> None:
        return None


class PolicyRouter(APIRouter):
    """A router about one subject, whose every route is guarded by a rule of its policy."""

    def __init__(self, *, subject: Subject | None, policy: type[Policy] = Policy, **kwargs: Any):
        self.subject = subject
        self.policy = policy
        super().__init__(**kwargs)

    def add_api_route(  # ty: ignore[invalid-method-override]
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        rule: Rule | Literal[_Public.PUBLIC],
        dependencies: Sequence[DependsParam] | None = None,
        **kwargs: Any,
    ) -> None:
        check = PublicCheck() if rule is PUBLIC else RuleCheck(self.policy, self.subject, rule)
        super().add_api_route(path, endpoint, dependencies=[*(dependencies or []), Depends(check)], **kwargs)
