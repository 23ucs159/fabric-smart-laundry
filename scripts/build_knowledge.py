"""Writes data/knowledge/care_rules.json (configurable care rules) and the RAG documents (*.md)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "knowledge"

def F(display, aliases, props, overview, wm, modes, temp, tmax, det, dry, dry_d, dry_n, iron, bleach, special, avoid, why):
    return dict(display=display, aliases=aliases, properties=props, overview=overview, washing_method=wm,
                wash_modes=modes, temperature=temp, max_temp_c=tmax, detergent=det, drying_method=dry,
                drying_with_dryer=dry_d, drying_without_dryer=dry_n, ironing=iron, bleaching=bleach,
                special_care=special, avoid=avoid, rationale=why)

RULES = {
 "cotton": F("Cotton", ["cotton"], ["breathable", "absorbent", "durable", "easy to wash"],
   "Cotton is a natural plant fibre that is breathable, absorbent and durable, and it handles regular washing well.",
   "Machine wash, normal or gentle cycle", ["Normal", "Gentle"], "30–40°C", 40,
   "Normal liquid or powder detergent; use a colour-safe detergent for dark colours",
   "Air dry or tumble dry low", "Tumble dry low", "Air dry (line dry in shade)",
   "Medium (up to 150°C)", "Oxygen bleach on whites only; avoid chlorine bleach on coloured cotton",
   "Avoid excessive heat, which can cause shrinkage; wash dark colours separately",
   "very hot water, overloading the drum, high-heat tumble drying",
   "Cotton generally tolerates moderate washing temperatures, so a 30–40°C wash is recommended."),
 "silk": F("Silk", ["silk", "satin silk"], ["smooth", "delicate", "lustrous", "heat sensitive"],
   "Silk is a fine natural protein fibre that is smooth and lustrous but weakens with heat, friction and harsh chemicals.",
   "Gentle hand wash or delicate machine cycle in a mesh bag", ["Delicate", "Hand wash"], "Cold, up to 30°C", 30,
   "Mild pH-neutral detergent made for delicates",
   "Air dry flat or hang in shade", "Do not tumble dry", "Air dry flat away from direct sunlight",
   "Low (up to 110°C), on the reverse side, no steam", "Do not bleach",
   "Avoid wringing, direct sunlight, and perfume or deodorant sprays that can stain",
   "chlorine bleach, wringing, hot water, long soaking",
   "Silk fibres weaken with heat and harsh detergents, so a gentle, cold wash is recommended."),
 "wool": F("Wool", ["wool", "woolen", "woollen", "cashmere"], ["warm", "elastic", "insulating", "shrink-prone"],
   "Wool is a natural animal fibre that is warm and elastic but shrinks and felts when exposed to heat and agitation.",
   "Wool or gentle cycle, or hand wash", ["Wool", "Gentle", "Hand wash"], "Cold, up to 30°C", 30,
   "Mild wool-safe detergent; avoid enzyme-based detergents",
   "Dry flat", "Do not tumble dry", "Dry flat on a towel and reshape while damp",
   "Low (up to 110°C) with a pressing cloth", "Do not bleach",
   "Avoid high heat and agitation, which cause felting and shrinkage; never hang heavy wet wool",
   "hot water, wringing, tumble drying, harsh detergents",
   "Wool shrinks and felts with heat and agitation, so a cold, gentle wash and flat drying are recommended."),
 "linen": F("Linen", ["linen", "flax"], ["breathable", "strong", "absorbent", "wrinkles easily"],
   "Linen is a strong natural fibre made from flax; it is cool and breathable but wrinkles easily.",
   "Machine wash, gentle or normal cycle", ["Gentle", "Normal"], "30–40°C", 40,
   "Mild detergent",
   "Air dry or tumble dry low", "Tumble dry low and remove while slightly damp", "Air dry; shake out and smooth while damp",
   "High (up to 200°C), ideally while damp or with steam", "Non-chlorine bleach on whites only",
   "Linen wrinkles easily, so iron while damp; over-drying makes it stiff",
   "chlorine bleach, over-drying, long soaking of coloured linen",
   "Linen is strong but wrinkles and stiffens when over-dried, so a moderate wash and damp ironing are recommended."),
 "polyester": F("Polyester", ["polyester", "poly"], ["durable", "quick-drying", "wrinkle resistant", "heat sensitive"],
   "Polyester is a durable synthetic fibre that dries quickly and resists wrinkles, but it is sensitive to high heat.",
   "Machine wash, normal or synthetic cycle", ["Normal", "Synthetic"], "30–40°C", 40,
   "Normal detergent",
   "Air dry or tumble dry low", "Tumble dry low", "Air dry",
   "Low (up to 110°C)", "Avoid chlorine bleach",
   "High heat can melt or permanently crease the fibres; avoid hot irons and high-heat dryers",
   "high heat, hot irons, fabric softener build-up",
   "Polyester is heat sensitive, so a moderate wash with a low-temperature iron is recommended."),
 "denim": F("Denim", ["denim", "jeans"], ["thick", "durable", "twill weave", "dye bleeds"],
   "Denim is a thick cotton twill that is dyed with indigo, which can fade and bleed in the wash.",
   "Machine wash inside out, normal cycle", ["Normal", "Gentle"], "30°C (cold to 30°C)", 30,
   "Mild detergent for dark colours",
   "Air dry or tumble dry low", "Tumble dry low", "Air dry inside out",
   "High (up to 200°C), inside out", "Do not bleach",
   "Wash inside out and separately at first because indigo dye can bleed; wash less often to preserve colour",
   "bleach, hot water, washing with light garments",
   "Denim dye fades with heat and friction, so a cool, inside-out wash is recommended."),
 "nylon": F("Nylon", ["nylon", "polyamide"], ["strong", "lightweight", "smooth", "heat sensitive"],
   "Nylon is a strong, lightweight synthetic fibre that is smooth and elastic but melts at high temperatures.",
   "Machine wash, gentle or synthetic cycle", ["Gentle", "Synthetic"], "30°C", 30,
   "Mild detergent",
   "Air dry or tumble dry low", "Tumble dry low", "Air dry",
   "Low (up to 110°C), or avoid ironing", "Do not use chlorine bleach (it causes yellowing)",
   "Heat can melt nylon; wash apart from lint-shedding fabrics and use a mesh bag for delicate items",
   "chlorine bleach, high heat, hot irons",
   "Nylon is strong but heat sensitive, so a gentle wash at a low temperature is recommended."),
 "rayon": F("Rayon", ["rayon", "viscose"], ["soft", "drapes well", "absorbent", "weak when wet"],
   "Rayon (viscose) is a soft, semi-synthetic fibre made from cellulose that drapes well but is weak when wet.",
   "Gentle machine cycle or hand wash", ["Gentle", "Hand wash"], "Cold, up to 30°C", 30,
   "Mild detergent",
   "Air dry; avoid wringing", "Tumble dry low only if the care label allows", "Air dry flat or on a padded hanger",
   "Low to medium (up to 150°C) on the reverse side", "Do not bleach",
   "Rayon is weak when wet, so avoid wringing and heat; shrinkage is possible",
   "wringing, hot water, high heat, long soaking",
   "Rayon loses strength when wet and shrinks with heat, so a gentle cold wash is recommended."),
 "velvet": F("Velvet", ["velvet", "velour"], ["soft pile", "luxurious", "delicate", "crush marks"],
   "Velvet has a soft raised pile that is easily crushed, and some velvets are dry-clean only.",
   "Gentle cycle or hand wash; check the label, some velvet is dry-clean only", ["Gentle", "Hand wash"], "Cold, up to 30°C", 30,
   "Mild detergent",
   "Air dry hanging, without wringing", "Do not tumble dry", "Air dry hanging",
   "Do not iron directly; steam from the reverse side", "Do not bleach",
   "Crushing the pile leaves marks; check the care label because some velvets are dry-clean only",
   "wringing, direct ironing, tumble drying",
   "Velvet's pile is easily crushed by heat and pressure, so a gentle cold wash with steam-only finishing is recommended."),
 "blended": F("Synthetic/Blended", ["synthetic", "blended", "blend", "mixed", "poly-cotton", "polycotton"],
   ["mixed fibres", "easy care", "heat sensitive", "varies by blend"],
   "Blended and synthetic fabrics combine fibres, so care must follow the most sensitive fibre in the mix.",
   "Machine wash, gentle or synthetic cycle", ["Gentle", "Synthetic"], "30°C", 30,
   "Mild or normal detergent",
   "Air dry or tumble dry low", "Tumble dry low", "Air dry",
   "Low (up to 110°C), following the most sensitive fibre", "Avoid bleach unless the label allows it",
   "Follow the care label and use the setting for the most delicate fibre; high heat may shrink, melt or crease the fabric",
   "high heat, hot irons, bleach",
   "Blends should be treated according to their most heat-sensitive fibre, so a gentle 30°C wash is recommended."),
}

GENERAL = {
 "general_laundry_safety": """# General laundry safety
## Check the care label first
The manufacturer care label is the most reliable source. If this application and the label disagree, follow the label.
## Sort before washing
Sort by colour and by fabric sensitivity. Wash delicates (silk, wool, rayon, velvet) separately from heavy items such as denim.
## Test for colour fastness
Dab an inside seam with a damp white cloth. If dye transfers, wash the item separately in cold water.
## High heat risk
High heat can shrink natural fibres and melt synthetic fibres such as polyester and nylon. When unsure, choose cold water, a gentle cycle and low heat.
## Safe handling
Keep detergents and bleach out of reach of children and never mix bleach with other cleaning products.
""",
 "washing_symbols": """# Washing symbols
## Wash tub symbol
A tub with a number shows the maximum wash temperature in degrees Celsius. A tub with a hand means hand wash only. A crossed-out tub means do not wash.
## Triangle symbol
An empty triangle allows any bleach. A triangle with two lines allows non-chlorine bleach only. A crossed-out triangle means do not bleach.
## Square symbol
A square with a circle is tumble drying. One dot means low heat and two dots mean medium heat. A crossed-out square means do not tumble dry. A square with a horizontal line means dry flat.
## Iron symbol
One dot means low heat up to 110°C, two dots medium up to 150°C and three dots high up to 200°C. A crossed-out iron means do not iron.
## Circle symbol
A circle means professional dry cleaning. A crossed-out circle means do not dry clean.
""",
 "detergent_guidance": """# Detergent guidance
## Mild detergent
Use a mild, pH-neutral detergent for silk, wool, rayon and velvet. Avoid enzyme detergents on silk and wool because enzymes attack protein fibres.
## Normal detergent
Cotton, linen, polyester and denim tolerate normal liquid or powder detergent. Use a colour-safe formula for dark or bright colours.
## How much to use
Follow the dose on the pack. Too much detergent leaves residue and can irritate skin.
## Fabric softener
Softener can reduce the absorbency of cotton towels and coat synthetic fibres, so use it sparingly or skip it.
""",
 "drying_methods": """# Drying methods
## Air drying
Air drying is the gentlest option. Dry in shade because strong sunlight can fade colours and weaken silk.
## Tumble drying
Tumble dry on low heat for cotton, linen, polyester, nylon and denim. Do not tumble dry silk, wool or velvet.
## Flat drying
Wool and other knits should be dried flat on a towel and reshaped while damp so they do not stretch.
## Hanging
Hang velvet, rayon and delicate shirts on padded hangers. Do not wring them.
""",
 "ironing_temperatures": """# Ironing temperatures
## Low heat
Low heat, up to 110°C, suits silk, wool, polyester, nylon and many blends. Use a pressing cloth for silk and wool.
## Medium heat
Medium heat, up to 150°C, suits cotton and rayon on the reverse side.
## High heat
High heat, up to 200°C, suits linen and denim, ideally with steam or while the fabric is damp.
## Velvet
Do not press velvet directly because the pile will crush. Steam it from the reverse side instead.
## Melting risk
Ironing a synthetic fabric on a high setting can melt or shine the fabric, so test on a hidden area.
""",
}

def doc_for(key, r):
    return f"""# {r['display']} care
## Overview
{r['overview']} Typical properties: {', '.join(r['properties'])}.
## Washing
Recommended washing: {r['washing_method']}. Recommended water temperature: {r['temperature']}. Detergent: {r['detergent']}. {r['rationale']}
## Drying
Recommended drying: {r['drying_method']}. With a dryer: {r['drying_with_dryer']}. Without a dryer: {r['drying_without_dryer']}.
## Ironing
Ironing temperature for {r['display'].lower()}: {r['ironing']}.
## Bleaching
Bleaching guidance: {r['bleaching']}.
## Special care and what to avoid
{r['special_care']}. Avoid: {r['avoid']}.
"""

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "care_rules.json").write_text(json.dumps(RULES, indent=2, ensure_ascii=False), encoding="utf-8")
    for key, r in RULES.items():
        (OUT / f"fabric_{key}_care.md").write_text(doc_for(key, r), encoding="utf-8")
    for name, text in GENERAL.items():
        (OUT / f"{name}.md").write_text(text, encoding="utf-8")
    print("wrote", len(RULES), "fabric docs and", len(GENERAL), "general docs")

if __name__ == "__main__":
    main()
