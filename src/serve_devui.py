#!/usr/bin/env python
# Copyright (c) Microsoft. All rights reserved.
"""Launch Prior Authorization Workflow in DevUI.

This script provides an easy way to start the PA workflow with DevUI
for interactive testing and development.

Usage:
    python serve_devui.py

    # Or with options:
    python serve_devui.py --port 8090 --no-auto-open
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Launch DevUI with the PA workflow."""
    parser = argparse.ArgumentParser(
        description="Launch Prior Authorization Workflow in DevUI"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run DevUI on (default: 8080)",
    )
    parser.add_argument(
        "--no-auto-open",
        action="store_true",
        help="Don't automatically open browser",
    )
    parser.add_argument(
        "--tracing",
        action="store_true",
        help="Enable OpenTelemetry tracing",
    )
    parser.add_argument(
        "--directory-mode",
        action="store_true",
        help="Use directory discovery instead of in-memory registration",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Import DevUI
    try:
        from agent_framework.devui import serve
    except ImportError:
        logger.error(
            "agent-framework-devui not installed. Install with:\n"
            "  pip install agent-framework-devui --pre"
        )
        sys.exit(1)

    print()
    print("=" * 70)
    print("  Prior Authorization Workflow - Microsoft Agent Framework DevUI")
    print("=" * 70)
    print()

    if args.directory_mode:
        # Use directory discovery
        entities_dir = str(Path(__file__).parent / "agenticai" / "devui_entities")
        print(f"Mode: Directory Discovery")
        print(f"Entities Directory: {entities_dir}")
        print()
        print(f"DevUI URL: http://localhost:{args.port}")
        print()
        print("=" * 70)

        serve(
            entities_dir=entities_dir,
            port=args.port,
            auto_open=not args.no_auto_open,
            tracing_enabled=args.tracing,
        )
    else:
        # Use in-memory registration
        from src.agenticai.devui_entities.pa_workflow.workflow import workflow

        print("Mode: In-Memory Registration")
        print()
        print(f"DevUI URL: http://localhost:{args.port}")
        print()
        print("Workflow: Prior Authorization Processing")
        print("  ├─ clinical_extractor: Extract patient/clinical data")
        print("  ├─ agentic_rag: Retrieve and evaluate policies")
        print("  └─ determination: Generate PA decision")
        print()
        print("Input Fields (PAProcessingRequest):")
        print("  • session_id: Unique session identifier")
        print("  • clinical_text: Clinical notes to process")
        print("  • procedure_codes: CPT/HCPCS codes (optional)")
        print("  • diagnosis_codes: ICD-10 codes (optional)")
        print()
        print("Example Input:")
        print('  {')
        print('    "session_id": "test-001",')
        print('    "clinical_text": "65-year-old male with severe osteoarthritis...",')
        print('    "procedure_codes": ["27447"],')
        print('    "diagnosis_codes": ["M17.11"]')
        print('  }')
        print()
        print("=" * 70)
        print()

        serve(
            entities=[workflow],
            port=args.port,
            auto_open=not args.no_auto_open,
            tracing_enabled=args.tracing,
        )


if __name__ == "__main__":
    main()
