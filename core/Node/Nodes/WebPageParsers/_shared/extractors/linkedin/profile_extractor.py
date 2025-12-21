import logging
from scrapy import Selector
from typing import Optional, List, Dict, Any
from ..core.utils import clean_text, parse_int
from .selectors.profile import ProfileSelectors

logger = logging.getLogger(__name__)


class LinkedInProfileExtractor:
    """
    Single extractor class for LinkedIn profiles.
    Same pattern as automation's ProfilePage - one class, multiple methods.
    """

    def __init__(self, html: str):
        logger.debug("Initializing LinkedInProfileExtractor with %d bytes of HTML", len(html))
        self.selector = Selector(text=html)
        self.selectors = ProfileSelectors(self.selector)

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════

    def extract(self) -> Dict[str, Any]:
        """Extract complete profile data."""
        logger.info("Starting profile extraction")
        data = {}

        # Header (name, headline, location)
        data.update(self.extract_header())

        # About
        data["about"] = self.extract_about()

        # Metrics (followers, connections)
        data.update(self.extract_metrics())

        # Experience
        data["experience"] = self.extract_experience()

        # Education
        data["education"] = self.extract_education()

        # Skills (just titles)
        data["skills"] = self.extract_skills()

        # Other sections
        data["licenses_and_certifications"] = self.extract_certifications()
        data["volunteering"] = self.extract_volunteering()
        data["projects"] = self.extract_projects()
        data["honors_and_awards"] = self.extract_honors()
        data["languages"] = self.extract_languages()
        data["publications"] = self.extract_publications()
        data["recommendations"] = self.extract_recommendations()

        # Count sections with data
        sections_with_data = sum(1 for key, val in data.items() if val)
        logger.info("Extraction complete - found %d sections with data", sections_with_data)

        return data

    # ═══════════════════════════════════════════════════════════════
    # HEADER EXTRACTION
    # ═══════════════════════════════════════════════════════════════

    def extract_header(self) -> Dict[str, str]:
        """Extract header: name, headline, location."""
        logger.debug("Extracting header section")
        section = self.selectors.header_section()
        if not section:
            logger.debug("Header section not found, returning empty values")
            return {"name": "", "headline": "", "location": ""}

        result = {
            "name": self._extract_first(self.selectors.name_xpaths(), section),
            "headline": self._extract_first(self.selectors.headline_xpaths(), section),
            "location": self._extract_first(self.selectors.location_xpaths(), section),
        }
        logger.debug("Header extracted: name=%s", result.get("name", ""))
        return result

    # ═══════════════════════════════════════════════════════════════
    # ABOUT EXTRACTION
    # ═══════════════════════════════════════════════════════════════

    def extract_about(self) -> str:
        """Extract about text from ABOUT_SECTION with global fallback."""
        logger.debug("Extracting about section")
        # Try section-based extraction first
        section = self.selectors.about_section()
        if section:
            result = self._extract_first(self.selectors.about_xpaths(), section)
            if result:
                logger.debug("About text extracted from section (%d chars)", len(result))
                return result

        # Fallback: global search using original XPaths
        logger.debug("Using global fallback for about section")
        global_about_xpaths = [
            './/div[contains(@class, "inline-show-more-text")]//span[@aria-hidden="true"]/text()',
            '//div[contains(@class, "pv-about__summary-text")]//text()',
            '//*[@id="about"]//following-sibling::div//span[@aria-hidden="true"]/text()',
        ]
        result = self._extract_first(global_about_xpaths, self.selector)
        if result:
            logger.debug("About text extracted from global fallback (%d chars)", len(result))
        return result

    # ═══════════════════════════════════════════════════════════════
    # METRICS EXTRACTION
    # ═══════════════════════════════════════════════════════════════

    def extract_metrics(self) -> Dict[str, int]:
        """Extract follower/connection counts."""
        logger.debug("Extracting metrics (followers/connections)")
        followers_raw = self._extract_first(
            self.selectors.followers_xpaths(), self.selector
        )
        connections_raw = self._extract_first(
            self.selectors.connections_xpaths(), self.selector
        )

        result = {
            "followers": parse_int(followers_raw),
            "connections": parse_int(connections_raw),
        }
        logger.debug("Metrics extracted: followers=%d, connections=%d",
                     result["followers"], result["connections"])
        return result

    # ═══════════════════════════════════════════════════════════════
    # SECTION EXTRACTORS
    # ═══════════════════════════════════════════════════════════════

    def extract_experience(self) -> List[Dict[str, Any]]:
        """Extract work experience."""
        logger.debug("Extracting experience section")
        section = self.selectors.experience_section()
        items = self._extract_section_items(section)
        logger.debug("Experience section - found %d items", len(items))
        return items

    def extract_education(self) -> List[Dict[str, Any]]:
        """Extract education history."""
        logger.debug("Extracting education section")
        section = self.selectors.education_section()
        items = self._extract_section_items(section)
        logger.debug("Education section - found %d items", len(items))
        return items

    def extract_skills(self) -> List[str]:
        """Extract skills as a flat list of titles."""
        logger.debug("Extracting skills section")
        section = self.selectors.skills_section()
        items = self._extract_section_items(section)
        skills = [item["title"] for item in items if item.get("title")]
        logger.debug("Skills section - found %d skills", len(skills))
        return skills

    def extract_certifications(self) -> List[Dict[str, Any]]:
        """Extract licenses and certifications."""
        logger.debug("Extracting certifications section")
        section = self.selectors.certifications_section()
        items = self._extract_section_items(section)
        logger.debug("Certifications section - found %d items", len(items))
        return items

    def extract_volunteering(self) -> List[Dict[str, Any]]:
        """Extract volunteering experience."""
        logger.debug("Extracting volunteering section")
        section = self.selectors.volunteering_section()
        items = self._extract_section_items(section)
        logger.debug("Volunteering section - found %d items", len(items))
        return items

    def extract_projects(self) -> List[Dict[str, Any]]:
        """Extract projects."""
        logger.debug("Extracting projects section")
        section = self.selectors.projects_section()
        items = self._extract_section_items(section)
        logger.debug("Projects section - found %d items", len(items))
        return items

    def extract_honors(self) -> List[Dict[str, Any]]:
        """Extract honors and awards."""
        logger.debug("Extracting honors section")
        section = self.selectors.honors_section()
        items = self._extract_section_items(section)
        logger.debug("Honors section - found %d items", len(items))
        return items

    def extract_languages(self) -> List[Dict[str, Any]]:
        """Extract languages."""
        logger.debug("Extracting languages section")
        section = self.selectors.languages_section()
        items = self._extract_section_items(section)
        logger.debug("Languages section - found %d items", len(items))
        return items

    def extract_publications(self) -> List[Dict[str, Any]]:
        """Extract publications."""
        logger.debug("Extracting publications section")
        section = self.selectors.publications_section()
        items = self._extract_section_items(section)
        logger.debug("Publications section - found %d items", len(items))
        return items

    def extract_recommendations(self) -> List[Dict[str, Any]]:
        """Extract recommendations."""
        logger.debug("Extracting recommendations section")
        section = self.selectors.recommendations_section()
        items = self._extract_section_items(section)
        logger.debug("Recommendations section - found %d items", len(items))
        return items

    # ═══════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═══════════════════════════════════════════════════════════════

    def _extract_section_items(
        self, section: Optional[Selector]
    ) -> List[Dict[str, Any]]:
        """Extract list items from a section."""
        if section is None:
            logger.debug("Section is None, returning empty list")
            return []

        items = []
        list_item_xpaths = self.selectors.list_item_xpaths()

        # Find all list items within the section
        item_nodes = []
        for xpath in list_item_xpaths:
            item_nodes = section.xpath(xpath)
            if item_nodes:
                break

        for node in item_nodes:
            entry = self._extract_item(node)
            items.append(entry)

        return items

    def _extract_item(self, item: Selector) -> Dict[str, Any]:
        """Extract fields from a list item."""
        entry = {}

        # Title
        entry["title"] = self._extract_first(
            self.selectors.item_title_xpaths(), item
        )

        # Subtitle
        entry["subtitle"] = self._extract_first(
            self.selectors.item_subtitle_xpaths(), item
        )

        # Meta fields (dates, locations, etc.)
        meta_vals = self._extract_all(self.selectors.item_meta_xpaths(), item)
        for i, val in enumerate(meta_vals):
            entry[f"meta_{i + 1}"] = val

        return entry

    def _extract_first(self, xpaths: List[str], context: Selector) -> str:
        """Try XPaths, return first match."""
        for xpath in xpaths:
            val = context.xpath(xpath).get()
            if val:
                cleaned = clean_text(val)
                if cleaned:
                    return cleaned
        return ""

    def _extract_all(self, xpaths: List[str], context: Selector) -> List[str]:
        """Try XPaths, return all matches from first successful."""
        for xpath in xpaths:
            vals = context.xpath(xpath).getall()
            if vals:
                return [clean_text(v) for v in vals if clean_text(v)]
        return []
