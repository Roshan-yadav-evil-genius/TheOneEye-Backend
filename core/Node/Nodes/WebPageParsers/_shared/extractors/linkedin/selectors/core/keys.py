from enum import Enum


class ProfileKey(Enum):
    # ═══════════════════════════════════════════════════════════════
    # Root Sections
    # ═══════════════════════════════════════════════════════════════
    HEADER_SECTION = "header_section"
    ABOUT_SECTION = "about_section"
    EXPERIENCE_SECTION = "experience_section"
    EDUCATION_SECTION = "education_section"
    SKILLS_SECTION = "skills_section"
    CERTIFICATIONS_SECTION = "certifications_section"
    VOLUNTEERING_SECTION = "volunteering_section"
    PROJECTS_SECTION = "projects_section"
    HONORS_SECTION = "honors_section"
    LANGUAGES_SECTION = "languages_section"
    PUBLICATIONS_SECTION = "publications_section"
    RECOMMENDATIONS_SECTION = "recommendations_section"

    # ═══════════════════════════════════════════════════════════════
    # Header Fields
    # ═══════════════════════════════════════════════════════════════
    NAME = "name"
    HEADLINE = "headline"
    LOCATION = "location"

    # ═══════════════════════════════════════════════════════════════
    # About Fields
    # ═══════════════════════════════════════════════════════════════
    ABOUT_TEXT = "about_text"

    # ═══════════════════════════════════════════════════════════════
    # Metrics
    # ═══════════════════════════════════════════════════════════════
    FOLLOWERS = "followers"
    CONNECTIONS = "connections"

    # ═══════════════════════════════════════════════════════════════
    # Section Items (used with parent context)
    # ═══════════════════════════════════════════════════════════════
    LIST_ITEM = "list_item"
    ITEM_TITLE = "item_title"
    ITEM_SUBTITLE = "item_subtitle"
    ITEM_META = "item_meta"
