"""Tests for company allowlist matching, academia drop, and US-only filters."""
import config
import industry


def test_allowlist_matches_affiliation_needles():
    assert industry.match_company("Waymo, Mountain View").name == "Waymo"
    assert industry.match_company("NVIDIA Research").name == "NVIDIA"
    assert industry.match_company("Toyota Research Institute").name == "Toyota Research"
    assert industry.match_company("Cruise LLC").name == "Cruise"
    assert industry.match_company("Meta AI").name == "Meta"
    assert industry.match_company("OpenAI").name == "OpenAI"
    assert industry.match_company("Plus AI").name == "Plus.ai"


def test_allowlist_matches_email_domains():
    assert industry.match_company("", "jane@waymo.com").name == "Waymo"
    assert industry.match_company("", "a@corp.uber.com").via == "email"
    assert industry.match_company("", "eng@nvidia.com").name == "NVIDIA"
    assert industry.match_company("MIT", "person@openai.com").name == "OpenAI"


def test_allowlist_does_not_match_unrelated_orgs():
    assert industry.match_company("Massachusetts Institute of Technology") is None
    assert industry.match_company("Oxford University") is None
    assert industry.match_company("Aurora University") is None  # not Aurora Innovation
    assert industry.match_company("", "jane@mit.edu") is None
    assert industry.match_company("Stanford University") is None


def test_word_boundary_avoids_substring_false_positives():
    assert industry.match_company("Stanford University") is None  # not Ford
    assert industry.match_company("Metabolic Imaging Lab") is None  # not Meta
    assert industry.match_company("Oxford Robotics") is None  # not Ford


def test_keep_candidate_requires_allowlist_company():
    assert industry.keep_candidate("Waymo, Mountain View") is True
    assert industry.keep_candidate("NVIDIA, Santa Clara") is True
    assert industry.keep_candidate("MIT CSAIL") is False
    assert industry.keep_candidate("Stanford University", "jane@stanford.edu") is False


def test_academia_only_edu_corresponding_author_dropped():
    """*.edu at a university with no company affiliation is dropped."""
    assert industry.keep_candidate(
        "University of California, Berkeley", "author@berkeley.edu"
    ) is False
    assert industry.is_academia("University of Texas", "a@utexas.edu") is True


def test_company_affiliation_kept_even_with_edu_email():
    """Industry affiliation wins over a leftover .edu corresponding-author address."""
    assert industry.keep_candidate("Waymo", "jane@cs.stanford.edu") is True


def test_company_email_kept_even_with_university_affiliation():
    assert industry.keep_candidate("Stanford University", "jane@nvidia.com") is True


def test_us_only_drops_foreign_offices():
    assert industry.keep_candidate("Google DeepMind, London") is False
    assert industry.keep_candidate("Intel, Haifa, Israel") is False
    assert industry.keep_candidate("Uber ATG, Toronto") is False
    assert industry.keep_candidate("Microsoft Research, Cambridge, UK") is False


def test_us_only_keeps_us_company_sites():
    assert industry.keep_candidate("Google, Mountain View") is True
    assert industry.keep_candidate("Tesla, Palo Alto") is True
    assert industry.keep_candidate("Anduril, Costa Mesa, California") is True
    assert industry.keep_candidate("", "eng@spacex.com") is True


def test_us_only_false_still_requires_company_but_allows_foreign():
    assert industry.keep_candidate("Google DeepMind, London", us_only=False) is True
    assert industry.keep_candidate("MIT", us_only=False) is False


def test_empty_affiliation_without_company_email_dropped():
    assert industry.keep_candidate("", "person@gmail.com") is False
    assert industry.keep_candidate("") is False


def test_shared_background_tamu_and_st_louis():
    assert industry.has_shared_background("Texas A&M University") is True
    assert industry.has_shared_background("raised in St. Louis") is True
    assert industry.has_shared_background("Waymo, Mountain View") is False


def test_allowlist_covers_requested_companies():
    names = {c["name"] for c in config.COMPANY_ALLOWLIST}
    expected = {
        "Uber", "Waymo", "DoorDash", "Lyft", "Trimble", "Zoox",
        "General Motors", "Cruise", "Two Sigma", "Google", "Apple",
        "Netflix", "Amazon", "Microsoft", "NVIDIA", "SpaceX", "Tesla",
        "Neuralink", "Meta", "OpenAI", "Aurora", "Motional", "Plus.ai",
        "Rivian", "Ford", "Toyota Research", "Intel", "Qualcomm",
        "Scale AI", "Anduril",
    }
    assert expected <= names


def test_positioning_is_networking_not_job_ask():
    text = config.POSITIONING.lower()
    assert "15" in config.POSITIONING and "20" in config.POSITIONING
    assert "referral" in text  # banned as "not a referral request"
    assert "not a job pitch" in text
    assert "internship" not in text
    assert "new-grad" not in text
    assert "open roles" not in text
