from scrapy import Selector
from typing import Optional, List
from ...core.base_selector import BaseSelector
from .core.keys import ProfileKey
from .core.registry import PROFILE_REGISTRY


class ProfileSelectors(BaseSelector):
    """
    Typed selector accessor for LinkedIn profiles.
    Same pattern as automation's LinkedInProfilePageSelectors.
    """

    def __init__(self, selector: Selector):
        super().__init__(selector, PROFILE_REGISTRY)

    # ═══════════════════════════════════════════════════════════════
    # Section Resolvers (return Selector objects)
    # ═══════════════════════════════════════════════════════════════

    def header_section(self) -> Optional[Selector]:
        """Resolve header section."""
        return self.resolve(ProfileKey.HEADER_SECTION)

    def about_section(self) -> Optional[Selector]:
        """Resolve about section."""
        return self.resolve(ProfileKey.ABOUT_SECTION)

    def experience_section(self) -> Optional[Selector]:
        """Resolve experience section."""
        return self.resolve(ProfileKey.EXPERIENCE_SECTION)

    def education_section(self) -> Optional[Selector]:
        """Resolve education section."""
        return self.resolve(ProfileKey.EDUCATION_SECTION)

    def skills_section(self) -> Optional[Selector]:
        """Resolve skills section."""
        return self.resolve(ProfileKey.SKILLS_SECTION)

    def certifications_section(self) -> Optional[Selector]:
        """Resolve certifications section."""
        return self.resolve(ProfileKey.CERTIFICATIONS_SECTION)

    def volunteering_section(self) -> Optional[Selector]:
        """Resolve volunteering section."""
        return self.resolve(ProfileKey.VOLUNTEERING_SECTION)

    def projects_section(self) -> Optional[Selector]:
        """Resolve projects section."""
        return self.resolve(ProfileKey.PROJECTS_SECTION)

    def honors_section(self) -> Optional[Selector]:
        """Resolve honors section."""
        return self.resolve(ProfileKey.HONORS_SECTION)

    def languages_section(self) -> Optional[Selector]:
        """Resolve languages section."""
        return self.resolve(ProfileKey.LANGUAGES_SECTION)

    def publications_section(self) -> Optional[Selector]:
        """Resolve publications section."""
        return self.resolve(ProfileKey.PUBLICATIONS_SECTION)

    def recommendations_section(self) -> Optional[Selector]:
        """Resolve recommendations section."""
        return self.resolve(ProfileKey.RECOMMENDATIONS_SECTION)

    # ═══════════════════════════════════════════════════════════════
    # Field XPaths (return XPath lists for extraction)
    # ═══════════════════════════════════════════════════════════════

    def name_xpaths(self) -> List[str]:
        return self.get(ProfileKey.NAME)

    def headline_xpaths(self) -> List[str]:
        return self.get(ProfileKey.HEADLINE)

    def location_xpaths(self) -> List[str]:
        return self.get(ProfileKey.LOCATION)

    def about_xpaths(self) -> List[str]:
        return self.get(ProfileKey.ABOUT_TEXT)

    def followers_xpaths(self) -> List[str]:
        return self.get(ProfileKey.FOLLOWERS)

    def connections_xpaths(self) -> List[str]:
        return self.get(ProfileKey.CONNECTIONS)

    # ═══════════════════════════════════════════════════════════════
    # Item XPaths (for list items within sections)
    # ═══════════════════════════════════════════════════════════════

    def list_item_xpaths(self) -> List[str]:
        return self.get(ProfileKey.LIST_ITEM)

    def item_title_xpaths(self) -> List[str]:
        return self.get(ProfileKey.ITEM_TITLE)

    def item_subtitle_xpaths(self) -> List[str]:
        return self.get(ProfileKey.ITEM_SUBTITLE)

    def item_meta_xpaths(self) -> List[str]:
        return self.get(ProfileKey.ITEM_META)
