"""
Code Review Agent - Code Quality and Review Management

Responsibilities:
- Code review coordination
- Quality gate enforcement
- Static analysis
- Code style checking
- Security scanning
- Review workflow management
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime


class ReviewStatus(Enum):
    """Code review status types"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMENTED = "commented"


class ReviewType(Enum):
    """Code review types"""
    PEER_REVIEW = "peer_review"
    TECHNICAL_REVIEW = "technical_review"
    SECURITY_REVIEW = "security_review"
    ARCHITECTURE_REVIEW = "architecture_review"
    CODE_REVIEW = "code_review"


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueType(Enum):
    """Code issue types"""
    BUG = "bug"
    VULNERABILITY = "vulnerability"
    CODE_SMELL = "code_smell"
    STYLE = "style"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FUNCTIONAL = "functional"
    DOCUMENTATION = "documentation"


@dataclass
class CodeReview:
    """Represents a code review"""
    review_id: str
    title: str
    description: str = ""
    review_type: ReviewType = ReviewType.CODE_REVIEW
    status: ReviewStatus = ReviewStatus.PENDING
    author: str = ""
    reviewers: List[str] = field(default_factory=list)
    repository: str = ""
    branch: str = ""
    commit_hash: str = ""
    files: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    merged_at: Optional[str] = None


@dataclass
class ReviewComment:
    """Represents a review comment"""
    comment_id: str
    review_id: str
    file: str
    line: int = 0
    position: int = 0
    comment: str = ""
    author: str = ""
    severity: Severity = Severity.MEDIUM
    issue_type: IssueType = IssueType.CODE_SMELL
    status: str = "open"  # "open", "resolved", "wont_fix"
    created_at: str = ""
    resolved_at: Optional[str] = None


@dataclass
class ReviewChecklist:
    """Represents a review checklist"""
    checklist_id: str
    name: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    required: bool = True


@dataclass
class QualityGate:
    """Represents a quality gate"""
    gate_id: str
    name: str
    description: str = ""
    checks: List[Dict[str, Any]] = field(default_factory=list)
    passing: bool = False
    results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeReviewAgent:
    """
    Code Review Agent
    
    This agent specializes in code review management, quality gates, and code quality enforcement.
    It coordinates code reviews, enforces standards, and ensures code quality.
    """
    
    agent_id: str = "code_review_agent_001"
    name: str = "Code Review"
    description: str = "Code quality and review management specialist"
    version: str = "1.0.0"
    
    # Code reviews
    code_reviews: Dict[str, CodeReview] = field(default_factory=dict)
    
    # Review comments
    review_comments: Dict[str, ReviewComment] = field(default_factory=dict)
    
    # Review checklists
    review_checklists: Dict[str, ReviewChecklist] = field(default_factory=dict)
    
    # Quality gates
    quality_gates: Dict[str, QualityGate] = field(default_factory=dict)
    
    # Current state
    current_review: Optional[str] = None
    current_gate: Optional[str] = None
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default checklists and gates"""
        self._initialize_checklists()
        self._initialize_quality_gates()
    
    def _initialize_checklists(self) -> None:
        """Initialize with default review checklists"""
        # Code quality checklist
        code_quality_checklist = ReviewChecklist(
            checklist_id="code_quality",
            name="Code Quality Checklist",
            required=True,
            items=[
                {"id": "readability", "description": "Code is readable and well-structured", "required": True},
                {"id": "naming", "description": "Variables and functions have meaningful names", "required": True},
                {"id": "comments", "description": "Code has appropriate comments and documentation", "required": False},
                {"id": "error_handling", "description": "Proper error handling is implemented", "required": True},
                {"id": "edge_cases", "description": "Edge cases are handled", "required": True},
                {"id": "performance", "description": "Code is efficient and performs well", "required": False},
                {"id": "security", "description": "No obvious security vulnerabilities", "required": True},
                {"id": "testing", "description": "Code has appropriate tests", "required": True}
            ]
        )
        self.review_checklists["code_quality"] = code_quality_checklist
        
        # Security review checklist
        security_checklist = ReviewChecklist(
            checklist_id="security_review",
            name="Security Review Checklist",
            required=True,
            items=[
                {"id": "input_validation", "description": "All inputs are properly validated", "required": True},
                {"id": "output_encoding", "description": "Outputs are properly encoded", "required": True},
                {"id": "authentication", "description": "Authentication is properly implemented", "required": True},
                {"id": "authorization", "description": "Authorization checks are in place", "required": True},
                {"id": "data_protection", "description": "Sensitive data is protected", "required": True},
                {"id": "dependency_security", "description": "Dependencies are secure and up-to-date", "required": True},
                {"id": "error_handling", "description": "Errors don't leak sensitive information", "required": True}
            ]
        )
        self.review_checklists["security_review"] = security_checklist
        
        # Architecture review checklist
        architecture_checklist = ReviewChecklist(
            checklist_id="architecture_review",
            name="Architecture Review Checklist",
            required=True,
            items=[
                {"id": "design_patterns", "description": "Appropriate design patterns are used", "required": False},
                {"id": "scalability", "description": "Solution is scalable", "required": True},
                {"id": "maintainability", "description": "Solution is maintainable", "required": True},
                {"id": "extensibility", "description": "Solution is extensible", "required": False},
                {"id": "performance", "description": "Architecture supports performance requirements", "required": True},
                {"id": "reliability", "description": "Solution is reliable and fault-tolerant", "required": True},
                {"id": "consistency", "description": "Architecture is consistent with existing systems", "required": False}
            ]
        )
        self.review_checklists["architecture_review"] = architecture_checklist
    
    def _initialize_quality_gates(self) -> None:
        """Initialize with default quality gates"""
        # Pre-commit gate
        pre_commit_gate = QualityGate(
            gate_id="pre_commit",
            name="Pre-Commit Gate",
            description="Checks that must pass before code can be committed",
            checks=[
                {"id": "linting", "description": "Code passes linting checks", "required": True},
                {"id": "formatting", "description": "Code is properly formatted", "required": True},
                {"id": "unit_tests", "description": "All unit tests pass", "required": True},
                {"id": "static_analysis", "description": "Static analysis passes", "required": True}
            ]
        )
        self.quality_gates["pre_commit"] = pre_commit_gate
        
        # Pre-merge gate
        pre_merge_gate = QualityGate(
            gate_id="pre_merge",
            name="Pre-Merge Gate",
            description="Checks that must pass before code can be merged",
            checks=[
                {"id": "code_review", "description": "Code has been reviewed and approved", "required": True},
                {"id": "integration_tests", "description": "Integration tests pass", "required": True},
                {"id": "coverage", "description": "Code coverage meets requirements", "required": True},
                {"id": "security_scan", "description": "Security scan passes", "required": True}
            ]
        )
        self.quality_gates["pre_merge"] = pre_merge_gate
        
        # Pre-release gate
        pre_release_gate = QualityGate(
            gate_id="pre_release",
            name="Pre-Release Gate",
            description="Checks that must pass before code can be released",
            checks=[
                {"id": "system_tests", "description": "System tests pass", "required": True},
                {"id": "performance_tests", "description": "Performance tests meet requirements", "required": True},
                {"id": "security_audit", "description": "Security audit passes", "required": True},
                {"id": "documentation", "description": "Documentation is complete", "required": True},
                {"id": "approval", "description": "Release is approved by stakeholders", "required": True}
            ]
        )
        self.quality_gates["pre_release"] = pre_release_gate
    
    async def create_review(self, review_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new code review
        
        Args:
            review_spec: Code review specification
            
        Returns:
            Dictionary with review configuration
        """
        print(f"🔍 {self.name}: Creating code review {review_spec.get('title', 'Unnamed')}")
        
        review_id = review_spec.get("review_id", f"review_{len(self.code_reviews) + 1}")
        title = review_spec.get("title", "Unnamed Review")
        description = review_spec.get("description", "")
        review_type_str = review_spec.get("review_type", "code_review")
        author = review_spec.get("author", "")
        reviewers = review_spec.get("reviewers", [])
        repository = review_spec.get("repository", "")
        branch = review_spec.get("branch", "")
        commit_hash = review_spec.get("commit_hash", "")
        files = review_spec.get("files", [])
        
        # Validate review type
        try:
            review_type = ReviewType(review_type_str)
        except ValueError:
            review_type = ReviewType.CODE_REVIEW
            print(f"⚠️  Review type {review_type_str} not valid, defaulting to CODE_REVIEW")
        
        # Create code review
        code_review = CodeReview(
            review_id=review_id,
            title=title,
            description=description,
            review_type=review_type,
            status=ReviewStatus.PENDING,
            author=author,
            reviewers=reviewers,
            repository=repository,
            branch=branch,
            commit_hash=commit_hash,
            files=files,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.code_reviews[review_id] = code_review
        self.current_review = review_id
        
        # Generate review summary
        review_summary = self._generate_review_summary(code_review)
        
        result = {
            "review_id": review_id,
            "title": title,
            "description": description,
            "review_type": review_type.value,
            "status": code_review.status.value,
            "author": author,
            "reviewers": reviewers,
            "repository": repository,
            "branch": branch,
            "commit_hash": commit_hash,
            "files": files,
            "summary": review_summary,
            "created_at": code_review.created_at,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Code review {title} created with ID {review_id}")
        return result
    
    def _generate_review_summary(self, review: CodeReview) -> Dict[str, Any]:
        """Generate a summary for a code review"""
        return {
            "review_id": review.review_id,
            "title": review.title,
            "type": review.review_type.value,
            "status": review.status.value,
            "author": review.author,
            "reviewers": review.reviewers,
            "files": review.files,
            "created_at": review.created_at,
            "statistics": {
                "files_changed": len(review.files),
                "reviewers_count": len(review.reviewers),
                "comments_count": len([c for c in self.review_comments.values() if c.review_id == review.review_id])
            }
        }
    
    async def add_comment(self, review_id: str, comment_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a comment to a code review
        
        Args:
            review_id: ID of the review
            comment_spec: Comment specification
            
        Returns:
            Dictionary with comment configuration
        """
        print(f"💬 {self.name}: Adding comment to review {review_id}")
        
        if review_id not in self.code_reviews:
            raise ValueError(f"Review {review_id} not found")
        
        comment_id = comment_spec.get("comment_id", f"comment_{len(self.review_comments) + 1}")
        file_path = comment_spec.get("file", "")
        line = comment_spec.get("line", 0)
        position = comment_spec.get("position", 0)
        comment = comment_spec.get("comment", "")
        author = comment_spec.get("author", "")
        severity_str = comment_spec.get("severity", "medium")
        issue_type_str = comment_spec.get("issue_type", "code_smell")
        
        # Validate severity
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.MEDIUM
            print(f"⚠️  Severity {severity_str} not valid, defaulting to MEDIUM")
        
        # Validate issue type
        try:
            issue_type = IssueType(issue_type_str)
        except ValueError:
            issue_type = IssueType.CODE_SMELL
            print(f"⚠️  Issue type {issue_type_str} not valid, defaulting to CODE_SMELL")
        
        # Create review comment
        review_comment = ReviewComment(
            comment_id=comment_id,
            review_id=review_id,
            file=file_path,
            line=line,
            position=position,
            comment=comment,
            author=author,
            severity=severity,
            issue_type=issue_type,
            status="open",
            created_at=datetime.now().isoformat()
        )
        
        self.review_comments[comment_id] = review_comment
        
        # Update review status if it was pending
        review = self.code_reviews[review_id]
        if review.status == ReviewStatus.PENDING:
            review.status = ReviewStatus.IN_PROGRESS
            review.updated_at = datetime.now().isoformat()
        
        result = {
            "comment_id": comment_id,
            "review_id": review_id,
            "file": file_path,
            "line": line,
            "position": position,
            "comment": comment,
            "author": author,
            "severity": severity.value,
            "issue_type": issue_type.value,
            "status": "open",
            "created_at": review_comment.created_at
        }
        
        print(f"✅ {self.name}: Comment {comment_id} added to review {review_id}")
        return result
    
    async def resolve_comment(self, comment_id: str, resolution: str = "resolved") -> Dict[str, Any]:
        """
        Resolve a review comment
        
        Args:
            comment_id: ID of the comment to resolve
            resolution: Resolution type ("resolved", "wont_fix")
            
        Returns:
            Dictionary with resolution results
        """
        print(f"✅ {self.name}: Resolving comment {comment_id}")
        
        if comment_id not in self.review_comments:
            raise ValueError(f"Comment {comment_id} not found")
        
        comment = self.review_comments[comment_id]
        
        # Update comment status
        comment.status = resolution
        comment.resolved_at = datetime.now().isoformat()
        
        # Update review status if all comments are resolved
        review = self.code_reviews[comment.review_id]
        open_comments = [
            c for c in self.review_comments.values() 
            if c.review_id == review.review_id and c.status == "open"
        ]
        
        if not open_comments:
            review.status = ReviewStatus.APPROVED
            review.updated_at = datetime.now().isoformat()
            review.merged_at = datetime.now().isoformat()
        
        result = {
            "comment_id": comment_id,
            "review_id": comment.review_id,
            "status": resolution,
            "resolved_at": comment.resolved_at,
            "review_status": review.status.value
        }
        
        print(f"✅ {self.name}: Comment {comment_id} resolved as {resolution}")
        return result
    
    async def approve_review(self, review_id: str, approver: str) -> Dict[str, Any]:
        """
        Approve a code review
        
        Args:
            review_id: ID of the review to approve
            approver: ID of the approver
            
        Returns:
            Dictionary with approval results
        """
        print(f"✅ {self.name}: Approving review {review_id}")
        
        if review_id not in self.code_reviews:
            raise ValueError(f"Review {review_id} not found")
        
        review = self.code_reviews[review_id]
        
        # Check if all comments are resolved
        open_comments = [
            c for c in self.review_comments.values() 
            if c.review_id == review_id and c.status == "open"
        ]
        
        if open_comments:
            raise ValueError(f"Cannot approve review with {len(open_comments)} open comments")
        
        # Update review status
        review.status = ReviewStatus.APPROVED
        review.updated_at = datetime.now().isoformat()
        review.merged_at = datetime.now().isoformat()
        
        # Add approver to reviewers if not already present
        if approver not in review.reviewers:
            review.reviewers.append(approver)
        
        result = {
            "review_id": review_id,
            "title": review.title,
            "status": review.status.value,
            "approver": approver,
            "merged_at": review.merged_at,
            "files": review.files
        }
        
        print(f"✅ {self.name}: Review {review_id} approved by {approver}")
        return result
    
    async def reject_review(self, review_id: str, rejecter: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject a code review
        
        Args:
            review_id: ID of the review to reject
            rejecter: ID of the rejecter
            reason: Reason for rejection
            
        Returns:
            Dictionary with rejection results
        """
        print(f"❌ {self.name}: Rejecting review {review_id}")
        
        if review_id not in self.code_reviews:
            raise ValueError(f"Review {review_id} not found")
        
        review = self.code_reviews[review_id]
        
        # Update review status
        review.status = ReviewStatus.REJECTED
        review.updated_at = datetime.now().isoformat()
        
        # Add rejection comment
        comment_id = f"rejection_{review_id}"
        rejection_comment = ReviewComment(
            comment_id=comment_id,
            review_id=review_id,
            file="",
            line=0,
            position=0,
            comment=f"Review rejected: {reason}",
            author=rejecter,
            severity=Severity.HIGH,
            issue_type=IssueType.FUNCTIONAL,
            status="open",
            created_at=datetime.now().isoformat()
        )
        
        self.review_comments[comment_id] = rejection_comment
        
        result = {
            "review_id": review_id,
            "title": review.title,
            "status": review.status.value,
            "rejecter": rejecter,
            "reason": reason,
            "rejection_comment_id": comment_id
        }
        
        print(f"✅ {self.name}: Review {review_id} rejected by {rejecter}")
        return result
    
    async def run_quality_gate(self, gate_id: str, gate_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a quality gate check
        
        Args:
            gate_id: ID of the quality gate
            gate_spec: Quality gate specification
            
        Returns:
            Dictionary with quality gate results
        """
        print(f"🚪 {self.name}: Running quality gate {gate_id}")
        
        if gate_id not in self.quality_gates:
            raise ValueError(f"Quality gate {gate_id} not found")
        
        gate = self.quality_gates[gate_id]
        
        # Run each check
        results = {}
        all_passing = True
        
        for check in gate.checks:
            check_id = check["id"]
            check_description = check["description"]
            required = check.get("required", True)
            
            # Simulate check result (in real implementation, this would run actual checks)
            if gate_id == "pre_commit":
                # Simulate pre-commit checks
                if check_id == "linting":
                    passed = True  # Assume linting passes
                elif check_id == "formatting":
                    passed = True  # Assume formatting passes
                elif check_id == "unit_tests":
                    passed = True  # Assume unit tests pass
                elif check_id == "static_analysis":
                    passed = True  # Assume static analysis passes
                else:
                    passed = False
            elif gate_id == "pre_merge":
                # Simulate pre-merge checks
                if check_id == "code_review":
                    # Check if there are any open reviews
                    open_reviews = [
                        r for r in self.code_reviews.values() 
                        if r.status != ReviewStatus.APPROVED
                    ]
                    passed = len(open_reviews) == 0
                elif check_id == "integration_tests":
                    passed = True  # Assume integration tests pass
                elif check_id == "coverage":
                    passed = True  # Assume coverage meets requirements
                elif check_id == "security_scan":
                    passed = True  # Assume security scan passes
                else:
                    passed = False
            elif gate_id == "pre_release":
                # Simulate pre-release checks
                if check_id == "system_tests":
                    passed = True  # Assume system tests pass
                elif check_id == "performance_tests":
                    passed = True  # Assume performance tests pass
                elif check_id == "security_audit":
                    passed = True  # Assume security audit passes
                elif check_id == "documentation":
                    passed = True  # Assume documentation is complete
                elif check_id == "approval":
                    passed = True  # Assume approval is granted
                else:
                    passed = False
            else:
                passed = False
            
            results[check_id] = {
                "description": check_description,
                "required": required,
                "passed": passed,
                "details": f"Check {check_id} {'passed' if passed else 'failed'}"
            }
            
            if required and not passed:
                all_passing = False
        
        # Update gate results
        gate.results = results
        gate.passing = all_passing
        
        # Generate gate report
        gate_report = self._generate_gate_report(gate)
        
        result = {
            "gate_id": gate_id,
            "name": gate.name,
            "description": gate.description,
            "passing": gate.passing,
            "results": results,
            "report": gate_report
        }
        
        if gate.passing:
            print(f"✅ {self.name}: Quality gate {gate_id} passed")
        else:
            print(f"❌ {self.name}: Quality gate {gate_id} failed")
        
        return result
    
    def _generate_gate_report(self, gate: QualityGate) -> Dict[str, Any]:
        """Generate a report for a quality gate"""
        report = {
            "gate_id": gate.gate_id,
            "name": gate.name,
            "description": gate.description,
            "passing": gate.passing,
            "summary": {
                "total_checks": len(gate.checks),
                "passed_checks": len([r for r in gate.results.values() if r["passed"]]),
                "failed_checks": len([r for r in gate.results.values() if not r["passed"]]),
                "required_checks": len([c for c in gate.checks if c.get("required", True)]),
                "required_passed": len([
                    r for r in gate.results.values() 
                    if r["required"] and r["passed"]
                ])
            },
            "checks": gate.results
        }
        
        # Add recommendations for failed checks
        failed_checks = [
            (check_id, result) for check_id, result in gate.results.items() 
            if not result["passed"] and result["required"]
        ]
        
        if failed_checks:
            report["recommendations"] = [
                f"Address failed check: {result['description']}" 
                for check_id, result in failed_checks
            ]
        
        return report
    
    async def check_checklist(self, checklist_id: str, item_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check items on a review checklist
        
        Args:
            checklist_id: ID of the checklist
            item_spec: Checklist item specification
            
        Returns:
            Dictionary with checklist results
        """
        print(f"✅ {self.name}: Checking checklist {checklist_id}")
        
        if checklist_id not in self.review_checklists:
            raise ValueError(f"Checklist {checklist_id} not found")
        
        checklist = self.review_checklists[checklist_id]
        
        # Check each item
        results = {}
        all_passed = True
        
        for item in checklist.items:
            item_id = item["id"]
            item_description = item["description"]
            required = item.get("required", True)
            
            # Simulate check result (in real implementation, this would check actual conditions)
            if checklist_id == "code_quality":
                # Simulate code quality checks
                if item_id == "readability":
                    passed = True
                elif item_id == "naming":
                    passed = True
                elif item_id == "comments":
                    passed = True
                elif item_id == "error_handling":
                    passed = True
                elif item_id == "edge_cases":
                    passed = True
                elif item_id == "performance":
                    passed = True
                elif item_id == "security":
                    passed = True
                elif item_id == "testing":
                    passed = True
                else:
                    passed = False
            elif checklist_id == "security_review":
                # Simulate security checks
                if item_id in ["input_validation", "output_encoding", "authentication", "authorization", "data_protection", "dependency_security", "error_handling"]:
                    passed = True
                else:
                    passed = False
            elif checklist_id == "architecture_review":
                # Simulate architecture checks
                if item_id in ["design_patterns", "scalability", "maintainability", "extensibility", "performance", "reliability", "consistency"]:
                    passed = True
                else:
                    passed = False
            else:
                passed = False
            
            results[item_id] = {
                "description": item_description,
                "required": required,
                "passed": passed
            }
            
            if required and not passed:
                all_passed = False
        
        # Generate checklist report
        checklist_report = {
            "checklist_id": checklist_id,
            "name": checklist.name,
            "all_passed": all_passed,
            "summary": {
                "total_items": len(checklist.items),
                "passed_items": len([r for r in results.values() if r["passed"]]),
                "failed_items": len([r for r in results.values() if not r["passed"]]),
                "required_items": len([i for i in checklist.items if i.get("required", True)]),
                "required_passed": len([
                    r for r in results.values() 
                    if r["required"] and r["passed"]
                ])
            },
            "results": results
        }
        
        result = {
            "checklist_id": checklist_id,
            "name": checklist.name,
            "all_passed": all_passed,
            "report": checklist_report
        }
        
        if all_passed:
            print(f"✅ {self.name}: Checklist {checklist_id} passed")
        else:
            print(f"❌ {self.name}: Checklist {checklist_id} failed")
        
        return result
    
    async def generate_review_report(self, review_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive review report
        
        Args:
            review_id: ID of the review
            
        Returns:
            Dictionary with review report
        """
        print(f"📄 {self.name}: Generating review report for {review_id}")
        
        if review_id not in self.code_reviews:
            raise ValueError(f"Review {review_id} not found")
        
        review = self.code_reviews[review_id]
        
        # Collect review data
        review_comments = [
            c for c in self.review_comments.values() 
            if c.review_id == review_id
        ]
        
        # Group comments by file
        comments_by_file = defaultdict(list)
        for comment in review_comments:
            comments_by_file[comment.file].append(comment)
        
        # Calculate statistics
        total_comments = len(review_comments)
        open_comments = len([c for c in review_comments if c.status == "open"])
        resolved_comments = len([c for c in review_comments if c.status == "resolved"])
        wont_fix_comments = len([c for c in review_comments if c.status == "wont_fix"])
        
        # Count by severity
        severity_counts = {
            "critical": len([c for c in review_comments if c.severity == Severity.CRITICAL]),
            "high": len([c for c in review_comments if c.severity == Severity.HIGH]),
            "medium": len([c for c in review_comments if c.severity == Severity.MEDIUM]),
            "low": len([c for c in review_comments if c.severity == Severity.LOW]),
            "info": len([c for c in review_comments if c.severity == Severity.INFO])
        }
        
        # Count by issue type
        issue_type_counts = {
            "bug": len([c for c in review_comments if c.issue_type == IssueType.BUG]),
            "vulnerability": len([c for c in review_comments if c.issue_type == IssueType.VULNERABILITY]),
            "code_smell": len([c for c in review_comments if c.issue_type == IssueType.CODE_SMELL]),
            "style": len([c for c in review_comments if c.issue_type == IssueType.STYLE]),
            "performance": len([c for c in review_comments if c.issue_type == IssueType.PERFORMANCE]),
            "security": len([c for c in review_comments if c.issue_type == IssueType.SECURITY]),
            "functional": len([c for c in review_comments if c.issue_type == IssueType.FUNCTIONAL]),
            "documentation": len([c for c in review_comments if c.issue_type == IssueType.DOCUMENTATION])
        }
        
        # Generate report
        report = {
            "review_id": review_id,
            "title": review.title,
            "description": review.description,
            "type": review.review_type.value,
            "status": review.status.value,
            "author": review.author,
            "reviewers": review.reviewers,
            "repository": review.repository,
            "branch": review.branch,
            "commit_hash": review.commit_hash,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "merged_at": review.merged_at,
            "statistics": {
                "files_changed": len(review.files),
                "total_comments": total_comments,
                "open_comments": open_comments,
                "resolved_comments": resolved_comments,
                "wont_fix_comments": wont_fix_comments,
                "comments_by_severity": severity_counts,
                "comments_by_type": issue_type_counts,
                "reviewers_count": len(review.reviewers),
                "review_duration": self._calculate_review_duration(review)
            },
            "files": {},
            "comments": [],
            "recommendations": self._generate_review_recommendations(review, review_comments)
        }
        
        # Add file-level statistics
        for file_path, comments in comments_by_file.items():
            file_stats = {
                "comments": len(comments),
                "open": len([c for c in comments if c.status == "open"]),
                "resolved": len([c for c in comments if c.status == "resolved"]),
                "by_severity": {
                    "critical": len([c for c in comments if c.severity == Severity.CRITICAL]),
                    "high": len([c for c in comments if c.severity == Severity.HIGH]),
                    "medium": len([c for c in comments if c.severity == Severity.MEDIUM]),
                    "low": len([c for c in comments if c.severity == Severity.LOW])
                }
            }
            report["files"][file_path] = file_stats
        
        # Add comments
        for comment in review_comments:
            report["comments"].append({
                "comment_id": comment.comment_id,
                "file": comment.file,
                "line": comment.line,
                "position": comment.position,
                "comment": comment.comment,
                "author": comment.author,
                "severity": comment.severity.value,
                "issue_type": comment.issue_type.value,
                "status": comment.status,
                "created_at": comment.created_at,
                "resolved_at": comment.resolved_at
            })
        
        print(f"✅ {self.name}: Review report generated for {review_id}")
        return report
    
    def _calculate_review_duration(self, review: CodeReview) -> str:
        """Calculate the duration of a review"""
        if review.merged_at:
            start = datetime.fromisoformat(review.created_at)
            end = datetime.fromisoformat(review.merged_at)
            duration = end - start
            
            days = duration.days
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        else:
            return "In progress"
    
    def _generate_review_recommendations(self, review: CodeReview, comments: List[ReviewComment]) -> List[str]:
        """Generate recommendations for a review"""
        recommendations = []
        
        # Check for critical issues
        critical_comments = [c for c in comments if c.severity == Severity.CRITICAL]
        if critical_comments:
            recommendations.append(f"Address {len(critical_comments)} critical issues before merging")
        
        # Check for security issues
        security_comments = [c for c in comments if c.issue_type == IssueType.SECURITY or c.issue_type == IssueType.VULNERABILITY]
        if security_comments:
            recommendations.append(f"Address {len(security_comments)} security issues immediately")
        
        # Check for open comments
        open_comments = [c for c in comments if c.status == "open"]
        if open_comments:
            recommendations.append(f"Resolve {len(open_comments)} open comments before approval")
        
        # Check for many comments on a single file
        comments_by_file = defaultdict(list)
        for comment in comments:
            comments_by_file[comment.file].append(comment)
        
        for file_path, file_comments in comments_by_file.items():
            if len(file_comments) > 10:
                recommendations.append(f"File {file_path} has {len(file_comments)} comments - consider refactoring")
        
        # Check for long review duration
        if review.merged_at:
            start = datetime.fromisoformat(review.created_at)
            end = datetime.fromisoformat(review.merged_at)
            duration = end - start
            
            if duration.days > 3:
                recommendations.append("Review took longer than 3 days - consider breaking into smaller changes")
        
        return recommendations
    
    async def get_review_status(self) -> Dict[str, Any]:
        """
        Get the current code review status
        
        Returns:
            Dictionary with code review status
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_review": self.current_review,
            "current_gate": self.current_gate,
            "code_reviews_count": len(self.code_reviews),
            "review_comments_count": len(self.review_comments),
            "review_checklists_count": len(self.review_checklists),
            "quality_gates_count": len(self.quality_gates),
            "performance_metrics": self.performance_metrics
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_review = None
        self.current_gate = None
        self.code_reviews.clear()
        self.review_comments.clear()
        self.review_checklists.clear()
        self.quality_gates.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
