"""SBOM + Vulnerability + Provenance Verification."""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SBOMVerifier:
    """Verify SBOM, signatures, and provenance."""
    
    def __init__(self):
        self.require_sbom = os.getenv("REQUIRE_SBOM", "false").lower() == "true"
        self.require_signature = os.getenv("REQUIRE_SIGNATURE", "false").lower() == "true"
        self.block_critical_cves = os.getenv("BLOCK_CRITICAL_CVES", "true").lower() == "true"
    
    def verify_image(self, image: str, image_digest: Optional[str] = None) -> Dict:
        """Verify image has SBOM, signature, and provenance."""
        # Extract image name and tag
        image_parts = image.split(":")
        image_name = image_parts[0] if len(image_parts) > 0 else image
        image_tag = image_parts[1] if len(image_parts) > 1 else "latest"
        
        # In production, this would query:
        # - Container registry for SBOM
        # - Cosign for signatures
        # - SLSA attestations for provenance
        
        # For now, simulate verification
        has_sbom = image_tag != "latest" and "@sha256:" in image
        has_signature = image_tag != "latest"
        has_provenance = image_tag != "latest"
        
        # Check for known vulnerabilities (simulated)
        vulnerabilities = []
        if "nginx:latest" in image.lower():
            vulnerabilities.append({
                "cve": "CVE-2024-XXXX",
                "severity": "high",
                "description": "Simulated vulnerability for latest tag"
            })
        
        risk_score = 0
        issues = []
        
        if not has_sbom and self.require_sbom:
            risk_score += 30
            issues.append("Missing SBOM")
        
        if not has_signature and self.require_signature:
            risk_score += 40
            issues.append("Image not signed")
        
        if not has_provenance:
            risk_score += 20
            issues.append("Missing provenance attestation")
        
        if vulnerabilities:
            critical_vulns = [v for v in vulnerabilities if v["severity"] in ["critical", "high"]]
            if critical_vulns and self.block_critical_cves:
                risk_score += 50
                issues.append(f"Critical vulnerabilities: {len(critical_vulns)}")
        
        return {
            "image": image,
            "image_digest": image_digest,
            "verification": {
                "has_sbom": has_sbom,
                "has_signature": has_signature,
                "has_provenance": has_provenance,
                "sbom_format": "cyclonedx" if has_sbom else None,
                "signature_verified": has_signature,
                "provenance_verified": has_provenance
            },
            "vulnerabilities": vulnerabilities,
            "risk_score": risk_score,
            "issues": issues,
            "blocked": risk_score >= 70 and self.block_critical_cves,
            "recommendations": [
                "Use signed images with SBOM",
                "Pin to specific digest instead of tags",
                "Enable provenance verification"
            ] if risk_score > 0 else []
        }
    
    def verify_digest_match(self, image_digest: str, attestation_digest: str) -> bool:
        """Verify image digest matches attestation digest."""
        return image_digest == attestation_digest


def verify_image_supply_chain(image: str, image_digest: Optional[str] = None) -> Dict:
    """Verify image supply chain security."""
    verifier = SBOMVerifier()
    return verifier.verify_image(image, image_digest)

