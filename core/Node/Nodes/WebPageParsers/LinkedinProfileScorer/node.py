"""
LinkedinProfileScorer Node

Single Responsibility: Score LinkedIn profiles based on intent and page content.
"""

from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import LinkedinProfileScorerForm

logger = structlog.get_logger(__name__)


class LinkedinProfileScorer(BlockingNode):
    """
    Score LinkedIn profiles based on user intent and page content.
    
    Takes 5 inputs:
    - intent: Free-form text describing what the user is looking for
    - profile_page_content: HTML from profile page
    - comment_page_content: HTML from comments page
    - posts_page_content: HTML from posts page
    - recent_reactions_content: HTML from recent reactions page
    
    Returns a scoring structure with overall score, category scores, and top posts.
    """
    
    @classmethod
    def identifier(cls) -> str:
        return "linkedin-profile-scorer"

    @property
    def label(self) -> str:
        """Display name for UI."""
        return "LinkedIn Profile Scorer"
    
    @property
    def description(self) -> str:
        """Node description for documentation."""
        return "Score LinkedIn profiles based on intent and page content"
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI."""
        return "score"

    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool - lightweight processing."""
        return PoolType.ASYNC

    def get_form(self) -> Optional[BaseForm]:
        return LinkedinProfileScorerForm()

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Score LinkedIn profile based on intent and page content.
        
        For now, returns empty skeleton structure with hardcoded values.
        Future implementation will parse HTML and calculate actual scores.
        
        Args:
            node_data: The NodeOutput from previous node.
            
        Returns:
            NodeOutput with scoring structure added to data.
        """
        # Retrieve inputs from form (already rendered if they contain Jinja templates)
        intent = self.form.cleaned_data.get("intent", "")
        profile_page_content = self.form.cleaned_data.get("profile_page_content", "")
        comment_page_content = self.form.cleaned_data.get("comment_page_content", "")
        posts_page_content = self.form.cleaned_data.get("posts_page_content", "")
        recent_reactions_content = self.form.cleaned_data.get("recent_reactions_content", "")
        
        logger.info(
            "Scoring LinkedIn profile",
            intent_length=len(intent),
            profile_content_length=len(profile_page_content),
            comment_content_length=len(comment_page_content),
            posts_content_length=len(posts_page_content),
            reactions_content_length=len(recent_reactions_content),
            node_id=self.node_config.id
        )
        
        # TODO: Parse HTML content and calculate actual scores
        # For now, return empty skeleton structure
        scoring_result = {
            "overallScore": 85,
            "categories": [
                {"name": "Posts", "score": 59},
                {"name": "Reactions", "score": 59},
                {"name": "Comments", "score": 59},
                {"name": "Profile", "score": 59},
                {"name": "Education", "score": 59}
            ],
            "topPosts": [{"label": "", "url": ""}]
        }
        
        output_key = self.get_unique_output_key(node_data, "linkedin_profile_score")
        node_data.data[output_key] = scoring_result
        
        logger.info(
            "LinkedIn profile scoring completed",
            overall_score=scoring_result["overallScore"],
            node_id=self.node_config.id
        )
        
        return node_data
