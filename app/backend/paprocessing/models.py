from typing import List, Optional

from pydantic import BaseModel


#
class PAProcessingRequest(BaseModel):
    """
    Request body format for initiating the PA Processing Pipeline.
    """

    uploaded_files: List[str]
    use_reasoning: bool = False
    caseId: Optional[str] = None
    streamlit: bool = False
