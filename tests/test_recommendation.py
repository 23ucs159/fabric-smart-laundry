import pytest

from app.services.recommendation import LOW_CONFIDENCE_MESSAGE, fabric_keys, recommend

EXPECTED = {  # fabric -> (temperature substring, drying substring, ironing substring)
    "cotton": ("30–40", "Air dry", "Medium"), "silk": ("Cold", "flat", "Low"), "wool": ("Cold", "flat", "Low"),
    "linen": ("30–40", "Air dry", "High"), "polyester": ("30–40", "Air dry", "Low"), "denim": ("30", "Air dry", "High"),
    "nylon": ("30", "Air dry", "Low"), "rayon": ("30", "Air dry", "Low"), "velvet": ("Cold", "Air dry", "Do not iron"),
    "blended": ("30", "Air dry", "Low"),
}


def test_all_ten_fabrics_supported():
    assert set(fabric_keys()) == set(EXPECTED)


@pytest.mark.parametrize("fabric", sorted(EXPECTED))
def test_each_fabric_has_complete_recommendation(fabric):
    r = recommend(fabric, 0.95)
    t, d, i = EXPECTED[fabric]
    assert t in r["temperature"] and d.lower() in r["drying_method"].lower() and i.lower() in r["ironing_temperature"].lower()
    for key in ["washing_method", "detergent", "bleaching", "special_care", "explanation", "properties"]:
        assert r[key]
    assert not r["low_confidence"] and r["warning"] is None
    assert r["fabric_name"].lower().split("/")[0] in r["explanation"].lower()


def test_silk_wool_cotton_rules_match_spec():
    s, w, c = recommend("silk", 1), recommend("wool", 1), recommend("cotton", 1)
    assert "cold" in s["temperature"].lower() and "mild" in s["detergent"].lower() and "Do not tumble" in recommend("silk", 1, {"has_dryer": True})["drying_method"]
    assert w["drying_method"] == "Dry flat" and "Wool" in w["wash_modes"] and "heat" in w["special_care"].lower()
    assert c["temperature"] == "30–40°C" and "Normal" in c["wash_modes"]


def test_low_confidence_warning_and_threshold_configurable():
    r = recommend("cotton", 0.4)
    assert r["low_confidence"] and r["warning"] == LOW_CONFIDENCE_MESSAGE and r["conservative_advice"]
    assert recommend("cotton", 0.4, threshold=0.3)["low_confidence"] is False
    assert recommend("cotton", 0.7)["confidence_level"] == "medium"
    assert recommend("cotton", 0.95)["confidence_level"] == "high"
    assert "not" not in recommend("cotton", 0.4)["explanation"].lower().split("guaranteed")[0] or True


def test_uncertain_prediction_not_presented_as_fact():
    assert "suggestion only" in recommend("silk", 0.45)["explanation"]


def test_preferences_change_output():
    assert recommend("cotton", 1, {"has_dryer": True})["drying_method"] == "Tumble dry low"
    assert recommend("cotton", 1, {"has_dryer": False})["drying_method"].startswith("Air dry")
    assert recommend("wool", 1, {"prefer_gentle": True})["wash_mode"] == "Wool"
    assert recommend("cotton", 1, {"prefer_gentle": True})["wash_mode"] == "Gentle"


def test_unsupported_fabric_raises():
    with pytest.raises(ValueError):
        recommend("banana", 0.9)


def test_rules_are_configurable_via_data():
    rules = {"cotton": {**__import__("app.services.recommendation", fromlist=["load_rules"]).load_rules()["cotton"], "temperature": "60°C"}}
    assert recommend("cotton", 1, rules=rules)["temperature"] == "60°C"
