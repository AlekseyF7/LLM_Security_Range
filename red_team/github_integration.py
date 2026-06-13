#!/usr/bin/env python3
"""
GitHub Integration for Red Team.
Automatically creates issues for successful attacks.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class AttackIssue:
    """Represents a successful attack to be reported as GitHub issue."""
    title: str
    description: str
    owasp_category: str
    severity: str
    labels: List[str]
    trace_id: Optional[str]
    langfuse_url: Optional[str]
    test_id: str
    attack_vector: str
    expected_block_layer: Optional[str]
    actual_result: str
    evidence: Dict[str, Any]


class GitHubIssueManager:
    """Manages creation of GitHub issues for successful attacks."""
    
    def __init__(
        self,
        repo_owner: str = None,
        repo_name: str = None,
        token: str = None,
        langfuse_base_url: str = "http://localhost:3000"
    ):
        self.repo_owner = repo_owner or os.getenv("GITHUB_REPO_OWNER")
        self.repo_name = repo_name or os.getenv("GITHUB_REPO_NAME")
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.langfuse_base_url = langfuse_base_url or os.getenv("LANGFUSE_URL", "http://localhost:3000")
        
        if not all([self.repo_owner, self.repo_name, self.token]):
            print("Warning: GitHub credentials not fully configured")
            self.enabled = False
        else:
            self.enabled = True
            self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues"
            self.headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
    
    def create_issue(self, attack: AttackIssue) -> Optional[str]:
        """Create a GitHub issue for a successful attack."""
        
        if not self.enabled:
            print(f"[DRY RUN] Would create issue: {attack.title}")
            return None
        
        # Build issue body
        body = self._build_issue_body(attack)
        
        # Prepare issue data
        issue_data = {
            "title": f"[RED TEAM] {attack.title}",
            "body": body,
            "labels": attack.labels,
            "assignees": []  # Can be configured per severity
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=issue_data,
                timeout=10
            )
            
            if response.status_code == 201:
                issue_data = response.json()
                issue_url = issue_data.get("html_url")
                issue_number = issue_data.get("number")
                print(f"Issue created: #{issue_number} - {issue_url}")
                return issue_url
            else:
                print(f"Failed to create issue: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating issue: {e}")
            return None
    
    def _build_issue_body(self, attack: AttackIssue) -> str:
        """Build markdown body for GitHub issue."""
        
        body_parts = [
            "## Attack Summary",
            "",
            f"**Test ID:** `{attack.test_id}`",
            f"**OWASP Category:** {attack.owasp_category}",
            f"**Severity:** {attack.severity}",
            f"**Attack Vector:** {attack.attack_vector}",
            "",
            "## Expected Behavior",
            "",
            f"Expected block layer: `{attack.expected_block_layer or 'Not specified'}`",
            "",
            "## Actual Result",
            "",
            f"**{attack.actual_result}**",
            "",
            "## Evidence",
            ""
        ]
        
        if attack.trace_id:
            langfuse_url = attack.langfuse_url or self._build_langfuse_url(attack.trace_id)
            body_parts.extend([
                f"**Langfuse Trace:** [View Trace]({langfuse_url})",
                f"**Trace ID:** `{attack.trace_id}`",
                ""
            ])
        
        if attack.evidence:
            body_parts.extend([
                "### Request Details",
                "```json",
                json.dumps(attack.evidence.get("request", {}), indent=2, ensure_ascii=False),
                "```",
                "",
                "### Response Details",
                "```json",
                json.dumps(attack.evidence.get("response", {}), indent=2, ensure_ascii=False),
                "```",
                ""
            ])
        
        body_parts.extend([
            "## Reproduction Steps",
            "",
            attack.description,
            "",
            "## Impact",
            "",
            self._get_impact_description(attack.severity, attack.owasp_category),
            "",
            "## Recommended Fix",
            "",
            self._get_recommended_fix(attack.owasp_category, attack.expected_block_layer),
            "",
            "---",
            f"*Auto-generated by Red Team automation at {datetime.now().isoformat()}*"
        ])
        
        return "\n".join(body_parts)
    
    def _build_langfuse_url(self, trace_id: str) -> str:
        """Build Langfuse trace URL."""
        return f"{self.langfuse_base_url}/trace/{trace_id}"
    
    def _get_impact_description(self, severity: str, owasp_category: str) -> str:
        """Get impact description based on severity and category."""
        
        impacts = {
            "critical": "This vulnerability allows attackers to bypass security controls and access sensitive information, potentially leading to full system compromise.",
            "high": "This vulnerability exposes sensitive information or allows unauthorized actions that could lead to significant security breaches.",
            "medium": "This vulnerability could be exploited to gain limited unauthorized access or information disclosure.",
            "low": "This vulnerability has limited impact but should be addressed to maintain defense in depth."
        }
        
        category_impacts = {
            "LLM01: Prompt Injection": "Attackers can manipulate the LLM to ignore safety guidelines and perform unauthorized actions.",
            "LLM03: Injection Attacks": "Attackers can inject malicious content through RAG documents, leading to data leaks.",
            "LLM06: Sensitive Information Disclosure": "Sensitive data including PII and credentials can be extracted from the system.",
            "LLM04: Model Denial of Service": "Attackers can exhaust system resources, causing service disruption."
        }
        
        base_impact = impacts.get(severity, "Security vulnerability detected.")
        category_impact = category_impacts.get(owasp_category, "")
        
        return f"{base_impact} {category_impact}".strip()
    
    def _get_recommended_fix(self, owasp_category: str, expected_layer: Optional[str]) -> str:
        """Get recommended fix based on OWASP category and expected layer."""
        
        fixes = {
            "LLM01: Prompt Injection": "Strengthen L1 Input Guard with additional jailbreak patterns and semantic analysis.",
            "LLM03: Injection Attacks": "Enhance L4 Output Guard with better fact-checking and canary token detection.",
            "LLM06: Sensitive Information Disclosure": "Improve PII detection in L4 Output Guard and implement stricter RBAC in L3.",
            "LLM04: Model Denial of Service": "Configure more aggressive rate limiting in L2 Behavioral Monitoring."
        }
        
        layer_fixes = {
            "L1_input_guard": "Review and update input guard patterns. Consider adding semantic similarity detection.",
            "L2_behavioral_monitoring": "Adjust rate limits and behavioral thresholds. Add IP-based tracking.",
            "L3_tool_access_control": "Review RBAC matrix and tool access policies.",
            "L4_output_guard": "Enhance output validation, fact-checking, and canary token detection."
        }
        
        category_fix = fixes.get(owasp_category, "Review and strengthen appropriate security layer.")
        
        if expected_layer:
            layer_fix = layer_fixes.get(expected_layer, "")
            return f"{category_fix}\n\nSpecifically for {expected_layer}: {layer_fix}"
        
        return category_fix


class AttackDetector:
    """Detects successful attacks from test results."""
    
    OWASP_MAPPING = {
        "DIR-": "LLM01: Prompt Injection",
        "IND-": "LLM03: Injection Attacks",
        "DATA-": "LLM06: Sensitive Information Disclosure",
        "TOOL-": "LLM07: Insecure Plugin Design",
        "BEH-": "LLM04: Model Denial of Service",
        "MAL-": "LLM02: Insecure Output Handling",
        "SYS-": "LLM01: Prompt Injection",
        "MT-": "LLM01: Prompt Injection",
        "LANGGRAPH-": "LLM01: Prompt Injection"
    }
    
    SEVERITY_MAPPING = {
        "critical": ["critical", "IND-", "DATA-", "SYS-"],
        "high": ["high", "DIR-", "TOOL-", "MAL-"],
        "medium": ["medium", "BEH-", "MT-"],
        "low": ["low"]
    }
    
    def __init__(self, langfuse_url: str = "http://localhost:3000"):
        self.langfuse_url = langfuse_url
    
    def analyze_promptfoo_results(self, results_file: Path) -> List[AttackIssue]:
        """Analyze promptfoo results for successful attacks."""
        
        issues = []
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        results = data.get("results", [])
        
        for result in results:
            if not result.get("success", True):
                test_id = self._extract_test_id(result)
                
                issue = AttackIssue(
                    title=f"Prompt Injection Bypass - {test_id}",
                    description=result.get("description", "No description"),
                    owasp_category=self._get_owasp_category(test_id),
                    severity=self._get_severity(test_id),
                    labels=self._build_labels(test_id, "promptfoo"),
                    trace_id=result.get("trace_id"),
                    langfuse_url=self._build_langfuse_url(result.get("trace_id")),
                    test_id=test_id,
                    attack_vector="direct_prompt",
                    expected_block_layer=self._extract_expected_layer(result),
                    actual_result="Attack succeeded - guard bypassed",
                    evidence={
                        "request": result.get("prompt", {}),
                        "response": result.get("response", {})
                    }
                )
                issues.append(issue)
        
        return issues
    
    def analyze_multi_turn_results(self, results_file: Path) -> List[AttackIssue]:
        """Analyze multi-turn results for successful attacks."""
        
        issues = []
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        results = data.get("results", [])
        
        for scenario in results:
            if not scenario.get("overall_passed", True):
                for turn in scenario.get("turns", []):
                    if not turn.get("passed", True):
                        issue = AttackIssue(
                            title=f"Multi-turn Attack - {scenario['scenario_id']} Turn {turn['turn']}",
                            description=self._build_multi_turn_description(scenario, turn),
                            owasp_category=self._get_owasp_category(scenario['scenario_id']),
                            severity=self._get_severity(scenario['scenario_id']),
                            labels=self._build_labels(scenario['scenario_id'], "multi-turn"),
                            trace_id=turn.get("trace_id"),
                            langfuse_url=self._build_langfuse_url(turn.get("trace_id")),
                            test_id=scenario['scenario_id'],
                            attack_vector="multi_turn_conversation",
                            expected_block_layer=turn.get("block_layer"),
                            actual_result=f"Turn {turn['turn']} bypassed guards",
                            evidence={
                                "scenario": scenario.get("name"),
                                "turn": turn.get("turn"),
                                "query": turn.get("query"),
                                "response": turn.get("response"),
                                "blocked": turn.get("blocked")
                            }
                        )
                        issues.append(issue)
        
        return issues
    
    def analyze_behavioral_results(self, results_file: Path) -> List[AttackIssue]:
        """Analyze behavioral results for successful attacks."""
        
        issues = []
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        summary = data.get("summary", {})
        results = data.get("results", {})
        
        if not summary.get("rate_flood_protected", True):
            issue = AttackIssue(
                title="Rate Limit Bypass Detected",
                description="Rate-flood attack was not properly blocked. System vulnerable to DoS.",
                owasp_category="LLM04: Model Denial of Service",
                severity="high",
                labels=["owasp/llm04-dos", "behavioral", "rate-limit"],
                trace_id=None,
                langfuse_url=None,
                test_id="BEH-RATE-001",
                attack_vector="rate_flood",
                expected_block_layer="L2_behavioral_monitoring",
                actual_result=f"Rate limit not triggered after {results.get('rate_flood', {}).get('total_requests', 0)} requests",
                evidence=results.get("rate_flood", {})
            )
            issues.append(issue)
        
        if not summary.get("session_pivot_protected", True):
            issue = AttackIssue(
                title="Session Pivot Rate Limit Bypass",
                description="Rate limiting can be bypassed by changing conversation sessions.",
                owasp_category="LLM04: Model Denial of Service",
                severity="medium",
                labels=["owasp/llm04-dos", "behavioral", "session-pivot"],
                trace_id=None,
                langfuse_url=None,
                test_id="BEH-PIVOT-001",
                attack_vector="session_pivot",
                expected_block_layer="L2_behavioral_monitoring",
                actual_result=f"Rate limit bypassed using {results.get('session_pivot', {}).get('total_sessions', 0)} sessions",
                evidence=results.get("session_pivot", {})
            )
            issues.append(issue)
        
        if not summary.get("jailbreak_counter_protected", True):
            issue = AttackIssue(
                title="Jailbreak Counter Not Triggered",
                description="Multiple jailbreak attempts did not trigger behavioral block.",
                owasp_category="LLM01: Prompt Injection",
                severity="high",
                labels=["owasp/llm01-injection", "behavioral", "jailbreak"],
                trace_id=None,
                langfuse_url=None,
                test_id="BEH-JAIL-001",
                attack_vector="repeated_jailbreak",
                expected_block_layer="L2_behavioral_monitoring",
                actual_result=f"{results.get('jailbreak_counter', {}).get('jailbreak_attempts', 0)} attempts without temp-block",
                evidence=results.get("jailbreak_counter", {})
            )
            issues.append(issue)
        
        return issues
    
    def _extract_test_id(self, result: Dict) -> str:
        """Extract test ID from result."""
        return result.get("description", "UNKNOWN")[:50]
    
    def _get_owasp_category(self, test_id: str) -> str:
        """Get OWASP category from test ID."""
        for prefix, category in self.OWASP_MAPPING.items():
            if test_id.startswith(prefix):
                return category
        return "LLM01: Prompt Injection"
    
    def _get_severity(self, test_id: str) -> str:
        """Get severity from test ID."""
        for severity, prefixes in self.SEVERITY_MAPPING.items():
            for prefix in prefixes:
                if prefix in test_id:
                    return severity
        return "medium"
    
    def _build_labels(self, test_id: str, test_type: str) -> List[str]:
        """Build GitHub labels."""
        labels = [
            "red-team",
            test_type,
            f"owasp/{self._get_owasp_category(test_id).lower().replace(' ', '-').replace(':', '')}"
        ]
        
        severity = self._get_severity(test_id)
        labels.append(f"severity/{severity}")
        
        return labels
    
    def _build_langfuse_url(self, trace_id: Optional[str]) -> Optional[str]:
        """Build Langfuse URL from trace ID."""
        if trace_id:
            return f"{self.langfuse_url}/trace/{trace_id}"
        return None
    
    def _extract_expected_layer(self, result: Dict) -> Optional[str]:
        """Extract expected block layer from result."""
        return result.get("expected_block_layer")
    
    def _build_multi_turn_description(self, scenario: Dict, turn: Dict) -> str:
        """Build description for multi-turn attack."""
        return f"""Scenario: {scenario.get('name', 'Unknown')}
Turn: {turn.get('turn', 0)}/{len(scenario.get('turns', []))}
Query: {turn.get('query', '')[:200]}
Response: {turn.get('response', '')[:200]}"""


def process_all_results(results_dir: Path, create_issues: bool = True) -> Dict[str, Any]:
    """Process all test results and create GitHub issues."""
    
    detector = AttackDetector()
    issue_manager = GitHubIssueManager()
    
    all_issues = []
    summary = {
        "total_issues": 0,
        "by_severity": {},
        "by_category": {},
        "by_test_type": {}
    }
    
    # Process promptfoo results
    promptfoo_files = results_dir.glob("promptfoo_*.json")
    for file in promptfoo_files:
        issues = detector.analyze_promptfoo_results(file)
        all_issues.extend(issues)
    
    # Process multi-turn results
    multi_turn_files = results_dir.glob("multi_turn_*.json")
    for file in multi_turn_files:
        issues = detector.analyze_multi_turn_results(file)
        all_issues.extend(issues)
    
    # Process behavioral results
    behavioral_dir = results_dir.parent / "behavioral" / "results"
    if behavioral_dir.exists():
        behavioral_files = behavioral_dir.glob("behavioral_tests_*.json")
        for file in behavioral_files:
            issues = detector.analyze_behavioral_results(file)
            all_issues.extend(issues)
    
    # Create issues and build summary
    created_issues = []
    
    for issue in all_issues:
        summary["total_issues"] += 1
        summary["by_severity"][issue.severity] = summary["by_severity"].get(issue.severity, 0) + 1
        summary["by_category"][issue.owasp_category] = summary["by_category"].get(issue.owasp_category, 0) + 1
        
        if create_issues:
            issue_url = issue_manager.create_issue(issue)
            if issue_url:
                created_issues.append({
                    "title": issue.title,
                    "url": issue_url,
                    "severity": issue.severity,
                    "category": issue.owasp_category
                })
        
        print(f"Issue detected: {issue.title} ({issue.severity})")
    
    # Save summary
    summary["created_issues"] = created_issues
    summary["issues"] = [
        {
            "title": i.title,
            "test_id": i.test_id,
            "severity": i.severity,
            "owasp_category": i.owasp_category,
            "trace_id": i.trace_id,
            "langfuse_url": i.langfuse_url
        }
        for i in all_issues
    ]
    
    summary_file = results_dir / f"issues_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"ISSUE CREATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total issues detected: {summary['total_issues']}")
    print(f"Issues created: {len(created_issues)}")
    print(f"\nBy severity:")
    for severity, count in summary['by_severity'].items():
        print(f"  {severity}: {count}")
    print(f"\nBy category:")
    for category, count in summary['by_category'].items():
        print(f"  {category}: {count}")
    print(f"\nSummary saved: {summary_file}")
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Issue Automation for Red Team")
    parser.add_argument("--results-dir", default="red_team/results", help="Results directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without creating issues")
    
    args = parser.parse_args()
    
    results_path = Path(args.results_dir)
    process_all_results(results_path, create_issues=not args.dry_run)
