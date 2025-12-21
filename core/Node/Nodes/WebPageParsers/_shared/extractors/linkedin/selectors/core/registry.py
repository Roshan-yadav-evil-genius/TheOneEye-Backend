from .keys import ProfileKey

# ═══════════════════════════════════════════════════════════════════════════════
# LinkedIn Profile Selector Registry
#
# Strategy:
# - Use parent hierarchy for scoped selectors (same pattern as automation)
# - Use generic container queries where possible
# - Prioritize ID and ARIA attributes over Tailwind classes
# ═══════════════════════════════════════════════════════════════════════════════

PROFILE_REGISTRY = {
    # ═══════════════════════════════════════════════════════════════
    # ROOT SECTIONS (no parent - searched from document root)
    # ═══════════════════════════════════════════════════════════════
    ProfileKey.HEADER_SECTION: {
        "selectors": [
            "//section[contains(@class, 'artdeco-card') and .//h1]",
            "//main//section[1]",
        ],
        "parent": None,
    },
    ProfileKey.ABOUT_SECTION: {
        "selectors": [
            "//section[.//*[@id='about']]",
            "//*[@id='about']/ancestor::section[1]",
            "//section[.//span[@id='about']]",
            "//section[.//h2//*[contains(text(), 'About')]]",
        ],
        "parent": None,
    },
    ProfileKey.EXPERIENCE_SECTION: {
        "selectors": [
            "//*[@id='experience']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Experience')]]",
        ],
        "parent": None,
    },
    ProfileKey.EDUCATION_SECTION: {
        "selectors": [
            "//*[@id='education']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Education')]]",
        ],
        "parent": None,
    },
    ProfileKey.SKILLS_SECTION: {
        "selectors": [
            "//*[@id='skills']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Skills')]]",
        ],
        "parent": None,
    },
    ProfileKey.CERTIFICATIONS_SECTION: {
        "selectors": [
            "//*[@id='licenses_and_certifications']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Licenses & certifications')]]",
        ],
        "parent": None,
    },
    ProfileKey.VOLUNTEERING_SECTION: {
        "selectors": [
            "//*[@id='volunteering_experience']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Volunteering')]]",
        ],
        "parent": None,
    },
    ProfileKey.PROJECTS_SECTION: {
        "selectors": [
            "//*[@id='projects']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Projects')]]",
        ],
        "parent": None,
    },
    ProfileKey.HONORS_SECTION: {
        "selectors": [
            "//*[@id='honors_and_awards']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Honors & awards')]]",
        ],
        "parent": None,
    },
    ProfileKey.LANGUAGES_SECTION: {
        "selectors": [
            "//*[@id='languages']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Languages')]]",
        ],
        "parent": None,
    },
    ProfileKey.PUBLICATIONS_SECTION: {
        "selectors": [
            "//*[@id='publications']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Publications')]]",
        ],
        "parent": None,
    },
    ProfileKey.RECOMMENDATIONS_SECTION: {
        "selectors": [
            "//*[@id='recommendations']/ancestor::section[1]",
            "//section[.//h2//*[contains(text(), 'Recommendations')]]",
        ],
        "parent": None,
    },
    # ═══════════════════════════════════════════════════════════════
    # HEADER FIELDS (scoped to HEADER_SECTION)
    # ═══════════════════════════════════════════════════════════════
    ProfileKey.NAME: {
        "selectors": [
            './/h1[contains(@class, "text-heading-xlarge")]/text()',
            ".//h1//text()",
        ],
        "parent": ProfileKey.HEADER_SECTION,
    },
    ProfileKey.HEADLINE: {
        "selectors": [
            './/div[contains(@class, "text-body-medium") and contains(@class, "break-words")]/text()',
            ".//div[@data-generated-suggestion-target]/text()",
        ],
        "parent": ProfileKey.HEADER_SECTION,
    },
    ProfileKey.LOCATION: {
        "selectors": [
            './/span[contains(@class, "text-body-small") and contains(@class, "inline") and contains(@class, "break-words")]/text()',
            './/div[contains(@class, "mt2")]//span[contains(@class, "text-body-small")]/text()',
        ],
        "parent": ProfileKey.HEADER_SECTION,
    },
    # ═══════════════════════════════════════════════════════════════
    # ABOUT FIELDS (scoped to ABOUT_SECTION)
    # ═══════════════════════════════════════════════════════════════
    ProfileKey.ABOUT_TEXT: {
        "selectors": [
            './/div[contains(@class, "inline-show-more-text")]//span[@aria-hidden="true"]/text()',
            '//div[contains(@class, "pv-about__summary-text")]//text()',
            '//*[@id="about"]//following-sibling::div//span[@aria-hidden="true"]/text()',
        ],
        "parent": ProfileKey.ABOUT_SECTION,
    },
    # ═══════════════════════════════════════════════════════════════
    # METRICS (global - no parent, searched from root)
    # ═══════════════════════════════════════════════════════════════
    ProfileKey.FOLLOWERS: {
        "selectors": [
            '//li//span[contains(text(), "followers")]/text()',
            '//*[contains(@class, "t-bold") and contains(text(), "followers")]/text()',
        ],
        "parent": None,
    },
    ProfileKey.CONNECTIONS: {
        "selectors": [
            '//span[contains(@class, "t-bold") and contains(text(), "500+")]/text()',
            '//span[contains(text(), "connections")]/text()',
        ],
        "parent": None,
    },
    # ═══════════════════════════════════════════════════════════════
    # SECTION ITEMS (no fixed parent - applied dynamically to section context)
    # ═══════════════════════════════════════════════════════════════
    ProfileKey.LIST_ITEM: {
        "selectors": [
            './/li[contains(@class, "artdeco-list__item")]',
            ".//li[contains(@class, 'pvs-list__paged-list-item')]",
        ],
        "parent": None,  # Applied dynamically
    },
    ProfileKey.ITEM_TITLE: {
        "selectors": [
            './/div[contains(@class, "display-flex")]//span[@aria-hidden="true"]/text()',
            './/span[@class="t-bold"]/text()',
            './/div[contains(@class, "t-bold")]/span/text()',
        ],
        "parent": None,  # Applied dynamically to item context
    },
    ProfileKey.ITEM_SUBTITLE: {
        "selectors": [
            './/span[contains(@class, "t-14")]//span[@aria-hidden="true"]/text()',
            './/span[contains(text(), "·")]/preceding-sibling::text()',
            './/span[contains(@class, "t-normal")]/span[@aria-hidden="true"]/text()',
        ],
        "parent": None,  # Applied dynamically to item context
    },
    ProfileKey.ITEM_META: {
        "selectors": [
            './/span[contains(@class, "t-black--light")]/span[@aria-hidden="true"]/text()',
            './/span[contains(@class, "t-black--light")]/text()',
        ],
        "parent": None,  # Applied dynamically to item context
    },
}
