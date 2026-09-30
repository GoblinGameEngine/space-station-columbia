#!/usr/bin/env python3
"""The name catalogue of the Columbia game bible: surnames and given names for every generation
aboard, from the founders (born on Earth, 2180-2252) to children born in the game's present (2752,
Voyage Year 500), as data the procedural engine draws from.

    python3 tools/bible/make_names.py            (make_bible.py calls this too)

Inputs (reference/names/, gitignored; public-domain US government data via GitHub mirrors, since
the census.gov and ssa.gov servers refuse scripted downloads):
  surnames.csv       2000 US Census surname file (151,671 names, >= 100 bearers each): count and
                     % white / Black / Asian-Pacific / American Indian-Alaska Native / two+ races /
                     Hispanic ("(S)" = suppressed, small). Mirror: fivethirtyeight/data.
  babynames_full.csv SSA national baby names 1880-2017, every name given to 5+ births (1,924,665
                     rows). Mirror: hadley/babynames (converted from babynames.rda).
Hand-built lists (from knowledge, marked as such): Quebec and Acadian surnames (under-represented
in US data), heritage given names (Hispanic/Mexican, francophone, African American, Arab, South
Asian, East Asian, Southeast Asian, African, Indigenous), the station's own coined names,
nicknames.

Method
------
SURNAMES
1. Founders (2252): 72,000 people drawn from the southern Great Lakes of 2250, the continent's
   climate refuge, whose families came from all of North America. Every census surname is
   reweighted from the 2000 US mix to the founders' target mix (FOUNDER_MIX) through its ethnic
   percentages, and Quebec/Acadian surnames are added at their own share.
2. Twenty generations (25 years each) of inheritance are simulated (a Galton-Watson branching
   process, deterministic seed): the population grows to the Balance of 250,000 by VY 118 and
   holds. Each surname line's bearers in the next generation are Poisson(count x growth). Under
   the Charter a child may take either parent's surname, which shortens the odds of extinction
   compared with patrilineal inheritance but doesn't change the expected growth. A few new
   surnames are coined each generation (foundlings and people who renamed themselves take a
   place or trade name).
   The result is the 2752 frequency of every surname, the founder effect included: common
   names more common, the long tail thinned, many founding names extinct. Snapshots at VY 100
   and VY 300 name historical people.
GIVEN NAMES
Pools of names, each with its own internal weights, mixed by birth cohort:
   earth_old (SSA 1880-1929), earth_mid (1930-1979), earth_new (1980-2017): the founders'
   continental naming, and the "grandparents' names" revivals that follow (Lieberson, *A Matter
   of Taste*, 2000: fashions cycle with the generations);
   heritage_<h>: a family's heritage names, weighted up by the surname's heritage;
   station: names the station coined (its lakes, creeks, towns, birds and plants, the voyage,
   virtues of the Balance);
   heroes: first names of the voyage's remembered people (filled from the people canon);
   vogue_<cohort>: each present-era decade's fashionable names.
The engine picks a pool by the cohort's mix (heritage raised by the family's heritage), then a
name within it.
"""
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REF = os.path.join(ROOT, "reference", "names")
SEED = 2252

# The founders' ancestry by census category (share of founders whose surname line comes from it).
# The 2250 Great Lakes refuge: an extrapolation of North America's trend (US Hispanic, Asian and
# multiracial shares rising; Canada's francophone and Mexico's Spanish-speaking populations part
# of the continental recruitment). Canon, not a forecast.
FOUNDER_MIX = {"white": 0.40, "hispanic": 0.27, "black": 0.15, "api": 0.11, "aian": 0.02, "multi": 0.025}
FRANCO_SHARE = 0.025              # Quebec, Acadian and Franco-Ontarian surnames, added separately
US2000 = {"white": 0.6928, "black": 0.1224, "api": 0.0338, "aian": 0.0067, "multi": 0.0153, "hispanic": 0.1266}
COLS = {"white": "pctwhite", "black": "pctblack", "api": "pctapi", "aian": "pctaian", "multi": "pct2prace", "hispanic": "pcthispanic"}
FOUNDERS = 72000
GENERATIONS = [(0, 72000), (25, 118000), (50, 172000), (75, 221000), (100, 246000), (125, 250000)]   # (VY, population) then held
GEN_YEARS = 25
COINED_PER_GEN = 0.0006           # share of each generation taking a new, station-coined surname

# -- hand lists (from knowledge; the census file under-represents these or can't tell them apart) --
QUEBEC = ("Tremblay Gagnon Roy Côté Bouchard Gauthier Morin Lavoie Fortin Gagné Ouellet Pelletier Bélanger Lévesque Bergeron Leblanc "
          "Paquette Girard Simard Boucher Caron Beaulieu Cloutier Dubé Poirier Fournier Lapointe Leclerc Lefebvre Poulin Thibault "
          "St-Pierre Nadeau Martel Bédard Grenier Lessard Bernier Michaud Hébert Desjardins Couture Turcotte Lachance Parent Blais "
          "Gosselin Savard Proulx Beaudoin Demers Perreault Boudreau Lemieux Cyr Perron Dufour Dion Mercier Bolduc Bérubé Boisvert "
          "Langlois Ménard Therrien Plante Bilodeau Blanchette Dubois Champagne Paradis Fortier Arsenault Dupuis Gaudreault Hamel "
          "Houle Villeneuve Rousseau Gravel Thériault Lemay Allard Deschênes Giroux Guay Leduc Boivin Charbonneau Lambert Vachon "
          "Audet Larouche Legault Trudel Fontaine Picard Labelle Lacroix Moreau Carrier Desrosiers Goulet Renaud Dionne Lapierre "
          "Vaillancourt Fillion Lalonde Tessier Tardif Lépine Lamontagne Labbé Auger Boudreault Cormier Doucet Landry Gallant "
          "LeBlanc Robichaud Arseneau Chiasson Thibodeau Babineau Gaudet").split()
SOUTH_ASIAN = set("PATEL SHAH SINGH KUMAR SHARMA GUPTA RAO REDDY DESAI MEHTA JOSHI IYER NAIR CHOWDHURY DAS SEN BOSE CHATTERJEE BANERJEE "
                  "MALHOTRA KAPOOR CHOPRA BHATT TRIVEDI PANDEY MISHRA VERMA AGARWAL JAIN GOEL KHANNA SETHI ARORA GILL SANDHU SIDHU DHILLON "
                  "GREWAL BRAR BAINS MANN SAINI VARGHESE KURIAN PILLAI MENON KRISHNAN SUBRAMANIAN RAMAN NARAYANAN SRINIVASAN "
                  "VENKATESAN GANESAN PRASAD CHAUDHARY YADAV TIWARI DUBEY SAXENA SRIVASTAVA BHATIA SURI AHUJA TALWAR ANAND BHARGAVA DUTTA "
                  "GHOSH MUKHERJEE ROY PARIKH MODI AMIN DAVE PANCHAL VYAS THAKKAR CHAUHAN RATHOD SOLANKI KHAN QURESHI SIDDIQUI SHAIKH "
                  "ANSARI HUSSAIN RAHMAN ISLAM HOSSAIN UDDIN MIAH CHOUDHURY BHUIYAN".split())
SE_ASIAN = set("NGUYEN TRAN LE PHAM HOANG HUYNH PHAN VU VO DANG BUI DO HO NGO DUONG LY TRUONG DINH LAM LUONG MAI TRINH CAO QUACH "
               "VANG XIONG YANG THAO MOUA HER LOR VUE LO KUE CHA HANG YANG KHANG SAECHAO SAEPHAN SOUVANNARATH PHOMMACHANH "
               "SANTOS DELA CRUZ BAUTISTA OCAMPO VILLANUEVA MACARAEG DIZON PANGILINAN AQUINO MANALO CASTILLO".split())
ARAB = set("HADDAD KHOURY SAAD HASSAN ALI AHMED MOHAMED MOHAMMED IBRAHIM ABDALLAH NASSER HAMAD MANSOUR KARAM NADER FARAH AZIZ BAZZI "
           "BERRY SALEH HAMMOUD FAWAZ BEYDOUN JABER KHALIL SALEM YOUSEF AWADA MAKKI AYOUB HARB SABBAGH MAALOUF RIZK HAMDAN ISSA "
           "SAID HAIDAR HAIDER ABBAS MOUSSA DAHER SLEIMAN KASSAB NAJJAR HADDAD SHAHEEN SHAHIN ASSAF HALABI SAAB ZEIN ELIAS KHALAF "
           "OMAR MUSA YASSIN DARWISH HUSSEIN HAMID AL-AMIN ALAMI".split())
GERMAN = set("MUELLER SCHNEIDER FISCHER WEBER WAGNER BECKER HOFFMAN HOFFMANN KOCH RICHTER KLEIN WOLF SCHRODER NEUMANN SCHWARZ ZIMMERMAN "
             "ZIMMERMANN BRAUN KRUGER HARTMANN LANGE WERNER KRAUSE LEHMANN KOHLER HERRMANN KONIG MAYER HUBER KAISER FUCHS SCHOLZ MOLLER "
             "FRANK BERGER WINKLER LORENZ BAUMANN ALBRECHT SIMON LUDWIG BOHM WINTER KRAUS MARTENS SCHUMACHER HEINRICH GRAF KESSLER "
             "HEIN HAHN VOGEL FRIEDRICH GUNTHER KELLER STAHL RITTER ENGEL HORN BUSCH KUHN POHL SAUER DIETRICH ROTH HAAS SCHAEFER "
             "SCHAFER EBERT JUNG BAUER STRAUSS BRANDT METZGER GEIGER GERBER HESS KNAPP KUNTZ LEHR LUTZ OTTO REUTER SEIFERT SPRINGER "
             "STEIGER STROH VOSS WAGNER YODER STOLTZFUS HERSHBERGER TROYER MAST MILLER HOCHSTETLER BONTRAGER BEACHY SCHROCK "
             "WEAVER".split()) - {"MILLER", "WEAVER"}
# Great Lakes flavour: the southern Great Lakes' own heritages, and a fuller South Asian share of the
# Asian founders (the 2000 census under-counts them against a 2250 continent)
SUB_BOOST = {"polish": 2.5, "hungarian": 3.0, "slavic": 2.0, "arab": 4.0, "italian": 1.3, "german": 1.15, "greek": 1.5, "dutch": 2.0,
             "irish_scots": 1.1, "south_asian": 2.6, "se_asian": 1.0, "east_asian": 0.85}
HUNGARIAN = set("KOVACS NAGY TOTH SZABO HORVATH VARGA KISS MOLNAR NEMETH FARKAS BALOGH PAPP TAKACS JUHASZ LAKATOS MESZAROS OLAH RACZ "
                "FEKETE SZILAGYI TOROK FEHER BALAZS GAL KIS SZUCS KOCSIS PINTER FODOR SZALAI SIPOS MAGYAR LUKACS GULYAS BIRO KIRALY "
                "KATONA JAKAB BOROS FAZEKAS KELEMEN ANTAL ORBAN SOOS HEGEDUS VINCZE VERES BUDAI CSONKA PATAKI SZEKELY GABOR".split())


def heritage_of(name, row):
    """The surname's heritage label (for lineage flavour and given-name heritage)."""
    n = name.upper()
    if n in SOUTH_ASIAN:
        return "south_asian"
    if n in SE_ASIAN:
        return "se_asian"
    if n in ARAB:
        return "arab"
    shares = {k: row.get(k, 0.0) for k in COLS}
    top = max(shares, key=shares.get)
    if top == "api":
        return "east_asian"
    if top == "hispanic":
        return "hispanic"
    if top == "black" and shares["black"] >= 55:
        return "black"
    if top == "aian" or shares["aian"] >= 30:
        return "indigenous"
    if top == "multi":
        return "multi"
    if shares["black"] >= 35:
        return "black_anglo"      # English-derived surnames shared by Black and white Americans
    return european_subheritage(n)


def european_subheritage(n):
    if n in HUNGARIAN:
        return "hungarian"
    if re.search(r"(SKI|SKY|CKI|CZYK|WICZ|CZAK|ZAK|IAK|EWSKI|OWSKI|CZ)$", n):
        return "polish"
    if re.search(r"(OV|OFF|EV|ENKO|CHUK|SHYN|YAK|UK|OVICH|EVICH|IC|ICH|OVIC|EVIC)$", n):
        return "slavic"
    if re.search(r"(OPOULOS|AKIS|IDES|IADIS|AKOS|OGLOU|IOU)$", n):
        return "greek"
    if re.search(r"^(MC|MAC|O')", n) or n in ("MURPHY", "KELLY", "SULLIVAN", "WALSH", "BYRNE", "RYAN", "OBRIEN", "CONNOR", "QUINN", "FLYNN", "BRENNAN", "DOYLE", "GALLAGHER", "DUNN", "KENNEDY", "LYNCH", "FITZGERALD", "BURKE", "HOGAN", "NOLAN"):
        return "irish_scots"
    if re.search(r"(INI|ELLI|ETTI|OTTI|ELLO|ANO|ONE|ACCI|UCCI|ARO|INO|ATO|ESE)$", n):
        return "italian"
    if re.search(r"^(VAN|VANDER|VANDE|DE[A-Z])", n) and re.search(r"(MA|STRA|INGA|HUIS|BERG|VELD|HOUT)$", n) or n.startswith("VANDER"):
        return "dutch"
    if re.search(r"(SSON|SEN|STROM|QVIST|LUND|GREN|DAHL|BERG|STAD)$", n):
        return "scandinavian"
    if n in GERMAN or re.search(r"(MANN|STEIN|BAUM|FELD|HEIM|HAUS|HOFF|DORF|STADT|BACH|MEIER|MEYER|SCHMIDT|SCHULTZ|SCHULZ|WEISS|ZWEIG|BRECHT|HARDT|WALD|LING|ZINGER|SINGER|BURGER)$", n) or n.startswith(("SCH", "WEI", "KRA", "KLO", "PF")):
        return "german"
    return "anglo"


def title(n):
    n = n.lower()
    out = "-".join(p[:1].upper() + p[1:] for p in n.split("-"))
    out = re.sub(r"^Mc([a-z])", lambda m: "Mc" + m.group(1).upper(), out)
    out = re.sub(r"^O'([a-z])", lambda m: "O'" + m.group(1).upper(), out)
    if re.match(r"^Mac[bcdfghjklmnpqrstvwz][a-z]{2,}", out) and out not in ("Mack", "Macy", "Machado", "Macias", "Mackey", "Macon"):
        out = "Mac" + out[3].upper() + out[4:]
    return out


def load_surnames():
    rows = []
    with open(os.path.join(REF, "surnames.csv")) as f:
        for r in csv.DictReader(f):
            vals = {}
            sup = []
            for k, col in COLS.items():
                v = r[col]
                if v.startswith("("):
                    sup.append(k)
                else:
                    vals[k] = float(v)
            rest = max(0.0, 100.0 - sum(vals.values()))
            for k in sup:
                vals[k] = rest / len(sup)
            rows.append((r["name"], int(r["count"]), vals))
    return rows


def founder_weights(rows):
    w = {}
    info = {}
    for name, count, vals in rows:
        if name in ("ALL OTHER NAMES",) or not re.match(r"^[A-Z'\-]+$", name):
            continue
        f = sum(vals[k] / 100.0 * FOUNDER_MIX[k] / US2000[k] for k in COLS)
        h = heritage_of(name, vals)
        w[name] = count * f * SUB_BOOST.get(h, 1.0)
        info[name] = (vals, h)
    tot = sum(w.values())
    for n in w:
        w[n] = w[n] / tot * (1.0 - FRANCO_SHARE)
    # Quebec and Acadian surnames: Zipf-like weights down the list
    z = [1.0 / (i + 1) ** 0.7 for i in range(len(QUEBEC))]
    zt = sum(z)
    for i, q in enumerate(QUEBEC):
        key = q.upper()
        w[key] = w.get(key, 0.0) + FRANCO_SHARE * z[i] / zt
        info[key] = ({"white": 100.0}, "francophone")
    return w, info


def simulate(w):
    """Founders to 2752 (VY 500): 20 generations of surname inheritance. Returns snapshots
    {vy: Counter(surname -> bearers)}."""
    rng = np.random.default_rng(SEED)
    names = list(w)
    p = np.array([w[n] for n in names])
    p /= p.sum()
    counts = rng.multinomial(FOUNDERS, p)
    cur = {names[i]: int(c) for i, c in enumerate(counts) if c > 0}
    snaps = {0: Counter(cur)}
    pop = FOUNDERS
    coined = 0
    for g in range(1, 21):
        vy = g * GEN_YEARS
        target = next((pp for y, pp in reversed(GENERATIONS) if vy >= y), 250000)
        growth = target / max(1, pop)
        ks = list(cur)
        lam = np.array([cur[k] for k in ks], dtype=float) * growth
        nxt = rng.poisson(lam)
        new = {k: int(c) for k, c in zip(ks, nxt) if c > 0}
        # coined names (foundlings, renamings): drawn from the station's place and trade names
        n_new = int(round(target * COINED_PER_GEN))
        for i in range(n_new):
            nm = COINED_SURNAMES[(g * 131 + i) % len(COINED_SURNAMES)].upper()
            new[nm] = new.get(nm, 0) + 1
            coined += 1
        # hold the population at the target (the Balance): rescale, keeping integer counts
        tot = sum(new.values())
        scale = target / tot
        cur = {k: max(1, int(round(c * scale))) if c * scale >= 0.5 else 0 for k, c in new.items()}
        cur = {k: c for k, c in cur.items() if c > 0}
        pop = sum(cur.values())
        snaps[vy] = Counter(cur)
    return snaps


COINED_SURNAMES = ("Tamsin Kettle Linden Heron Sedge Willow Carrow Brannock Harrow Solana Haven Tern Marlowe Fenwick Tanner Birch Cedar "
                   "Keeper Tender Sunline Spinward Northway Bowman Sternman Undercroft Commons Balance Voyager Lumen Waymaker Draw "
                   "Brightwater Oceanview Pruett Loomis Dunmore Haskins Kessler Bellhaven Tamarack Victory Ford Mill Quarry Sauk Otter "
                   "Plum Ash Fox Deer Brush Cole Sedgewick Lakeman Shoreman Fisher Weaver Grower Hydro Vatman").split()

# ---------------------------------------------------------------------------------------------------------
# given names
EARTH_POOLS = {"earth_old": (1880, 1929), "earth_mid": (1930, 1979), "earth_new": (1980, 2017)}
POOL_TOP = 1500


def load_given():
    pools = {p: {"F": Counter(), "M": Counter()} for p in EARTH_POOLS}
    with open(os.path.join(REF, "babynames_full.csv")) as f:
        for r in csv.DictReader(f):
            y = int(float(r["year"]))
            for p, (a, b) in EARTH_POOLS.items():
                if a <= y <= b:
                    pools[p][r["sex"]][r["name"]] += int(float(r["n"]))
    out = {}
    for p in pools:
        out[p] = {}
        for s in ("F", "M"):
            top = pools[p][s].most_common(POOL_TOP)
            tot = sum(c for _, c in top)
            out[p][s] = [[n, round(c / tot * 1e6, 1)] for n, c in top]
    return out


H = {
 "hispanic": {
  "M": "José Juan Luis Carlos Jesús Miguel Francisco Alejandro Jorge Antonio Pedro Manuel Santiago Mateo Sebastián Leonardo Emiliano Diego Javier Ricardo Fernando Eduardo Rafael Roberto Arturo Andrés Raúl Ramón Héctor Sergio Víctor Óscar Armando Guillermo Enrique Joaquín Emilio Julio Tomás Ignacio Rodrigo Gerardo Alfredo Salvador Rubén Esteban Ángel Gabriel Iker Thiago Gael Maximiliano Damián Adrián Nicolás Valentín Rogelio Efraín Aurelio Lázaro Ernesto Marco Benicio Elías Isidro Jacinto Teodoro Cruz Santos Ulises Octavio Horacio Abel Álvaro Bernardo Camilo Cristóbal Domingo Fabián Hugo Mauricio Noé Pablo Reynaldo Saúl",
  "F": "María Guadalupe Juana Margarita Verónica Leticia Rosa Ana Sofía Valentina Regina Ximena Camila Fernanda Renata Victoria Isabella Lucía Daniela Mariana Gabriela Alejandra Paola Andrea Carmen Elena Esperanza Dolores Pilar Consuelo Luz Marisol Yolanda Graciela Beatriz Adriana Claudia Mónica Patricia Rocío Araceli Itzel Citlali Xóchitl Yesenia Maribel Josefina Inés Luciana Catalina Emilia Julieta Paloma Estrella Celeste Brisa Esmeralda Azucena Noemí Soledad Amparo Milagros Belén Abril Frida Natalia Karla Lourdes Mercedes Reina Socorro Teresa Aurora Ofelia Rosario Maricela Nayeli Dulce Perla Montserrat Salomé"},
 "francophone": {
  "M": "Jean Marc Luc Pierre Mathieu Olivier Gabriel Félix Étienne Guillaume Maxime Alexandre Samuel Louis Antoine Philippe Julien Émile Léo Hugo Rémi Benoît Denis Gilles Yves Réjean Gaétan Normand Sylvain François Xavier Nicolas Vincent Jacques Laurent Mathis Thomas Raphaël Jérôme Martin Donat Fernand Lucien Marcel Armand Hervé Aurèle Clément Édouard Jules",
  "F": "Marie Léa Chloé Émilie Camille Sophie Geneviève Catherine Julie Isabelle Nathalie Josée Manon Sylvie Mélanie Stéphanie Zoé Alice Florence Rosalie Juliette Béatrice Léonie Élodie Amélie Maude Marguerite Lucie Céline Chantal Diane Ginette Monique Hélène Solange Madeleine Simone Anaïs Clémence Maëlle Yvette Jeanne Odette Gisèle Thérèse Blanche Lise Pascale Colette Rachelle"},
 "black": {
  "M": "Jamal DeShawn Darnell Tyrone Malik Andre Terrell Marquis Jalen Jaylen Darius Xavier Isaiah Elijah Josiah Cornelius Rashad Jermaine Cedric Reginald Demetrius Kareem Tariq Khalil Omari Amari Kwame Desmond Lamar Marcus Maurice Roosevelt Booker Otis Langston Thurgood Ezekiel Zion Kendrick Dante Jabari Alonzo Clarence Percy Wendell Julius Solomon Dorian Quincy Tobias",
  "F": "Imani Aaliyah Keisha Latoya Ebony Jasmine Tamika Destiny Nia Aisha Kiara Jada Maya Zora Toni Octavia Coretta Rosa Harriet Ayanna Nyla Amara Journee Serenity Essence Tanisha Shanice Kenya Asia Precious Dominique Monique Janelle Brianna Laila Zuri Kamaria Nala Ruby Mahalia Odessa Lorraine Bessie Etta Alberta Hattie Viola Fannie Pearl"},
 "arab": {
  "M": "Muhammad Ahmad Ali Hassan Hussein Omar Yusuf Ibrahim Khalid Karim Tariq Samir Nabil Rami Ziad Fadi Jamal Bilal Mustafa Adam Amir Zayd Hamza Mahmoud Walid Faris Nasser Elias Georges Michel Antoine Jad Rayan Yasin Idris Kamal Saleh Hadi Wael Majid",
  "F": "Fatima Layla Zainab Maryam Aisha Nour Rania Hala Yasmin Lina Dina Salma Amira Hiba Rana Maya Nadia Samira Leila Jana Mira Rima Zeina Hanan Huda Aya Sara Farah Noor Reem Najwa Mona Ghada Lamia Suha"},
 "south_asian": {
  "M": "Aarav Arjun Rohan Vikram Rahul Ravi Sanjay Anil Raj Amit Nikhil Aditya Karan Dev Vivek Suresh Ramesh Deepak Arun Pranav Ishaan Vihaan Krishna Siddharth Harpreet Gurpreet Jaspreet Imran Faisal Zain Ayaan Kabir Neel Tarun Sameer Ashok Vijay Ajay Rakesh Manish Gaurav Varun Hari Sunil",
  "F": "Priya Anjali Neha Pooja Divya Kavya Ananya Aanya Diya Isha Meera Riya Sanjana Shreya Aditi Lakshmi Sunita Anita Geeta Nisha Tara Radha Sita Deepa Sarita Kiran Simran Navneet Harleen Ayesha Sana Zara Saanvi Nandini Kalpana Asha Uma Leela Mira Jaya Rekha Padma Veena"},
 "east_asian": {
  "M": "Wei Jun Hao Jian Ming Lei Yong Kai Hiro Kenji Takeshi Haruto Ren Sota Minjun Seojun Jiho Joon Hyun Sung Tae Kenzo Akira Shin Yuto Zhi Bo Tian Chang Feng Jin Daiki Kaito Riku Yuki",
  "F": "Mei Lin Xiu Ying Hui Li Jing Yan Hana Yuki Sakura Aiko Emi Yui Mio Rin Seoyeon Jiwoo Minseo Sooah Eun Hyejin Haeun Mika Naomi Nari Yuna Ai Xiao Lan Chun Fang Keiko Midori Sumi"},
 "se_asian": {
  "M": "Minh Tuan Duc Huy Khoa Long Nam Quang Thanh Hung Bao Phuc Tai Vinh Kou Tou Neng Somchai Arnel Rommel Jomar Jericho Dang Hieu Khang Phong Tam Toan Chue Pheng",
  "F": "Linh Lan Mai Ngoc Thu Trang Hoa Huong Nga Thao Vy Yen Kim My Tien Hanh Malai Maricel Rowena Lorna Liza Angelica Divina Luzviminda Mai Nou Pa Houa Kia Bao Diem Phuong"},
 "african": {
  "M": "Chidi Emeka Chinedu Obinna Tunde Femi Seun Kwame Kofi Kwaku Yaw Abdi Abebe Dawit Tesfaye Yonas Kelechi Uche Ade Babajide Olu Nnamdi Ikenna Jabari Baraka Juma Musa Amadou Moussa Mamadou Ousmane Ibrahima Tendai Tafadzwa",
  "F": "Ngozi Chioma Adaeze Amaka Nneka Ifeoma Chiamaka Folake Yetunde Funmilayo Abena Akosua Ama Efua Adwoa Hodan Ayan Sagal Selam Meron Tigist Liya Makeda Ayo Zawadi Neema Fatoumata Aminata Mariama Nkechi Adanna Oluwaseun Rutendo"},
 "indigenous": {
  "M": "Tecumseh Takoda Chayton Dakota Sequoyah Nodin Ahanu Hinto Kele Mato Wapi Kitchi Enapay Tokala",
  "F": "Aiyana Winona Kiona Tallulah Cheyenne Nokomis Sequoia Aponi Winona Kimi Halona Mika Tayanita Wenonah Onawa"},
}
H["black_anglo"] = H["black"]
NOTE_INDIGENOUS = ("Indigenous given names are a short list from knowledge and must be reviewed with community sources before use; most "
                   "Indigenous families (like most families) draw on the general pools.")

STATION = {
 # (name, sex F/M/U, source)
 "geography": [("Tamsin", "F"), ("Linden", "U"), ("Willow", "F"), ("Sedge", "M"), ("Heron", "U"), ("Birch", "U"), ("Cedar", "U"),
               ("Ash", "M"), ("Plum", "F"), ("Tanner", "M"), ("Cole", "M"), ("Sauk", "M"), ("Brannock", "M"), ("Carrow", "M"), ("Marlowe", "U"),
               ("Haven", "F"), ("Solana", "F"), ("Tern", "U"), ("Victory", "F"), ("Harrow", "M"), ("Fenwick", "M"), ("Tamarack", "M"),
               ("Kessler", "M"), ("Loomis", "M"), ("Pruett", "M"), ("Dunmore", "M"), ("Kettle", "M"), ("Brightwater", "F"), ("Bellhaven", "F"),
               ("Linnet", "F"), ("Otter", "M")],
 "great_lakes_memory": [("Erie", "F"), ("Huron", "M"), ("Maumee", "F"), ("Cleveland", "M"), ("Mackinac", "M"), ("Ottawa", "F"), ("Cuyahoga", "F"),
                        ("Chicago", "M"), ("Tole", "M"), ("Superior", "M"), ("Ontario", "F"), ("Sandusky", "M"), ("Muskegon", "M"), ("Saginaw", "F")],
 "voyage": [("Hesper", "F"), ("Lumen", "U"), ("Vega", "F"), ("Rigel", "M"), ("Aster", "F"), ("Sol", "M"), ("Celeste", "F"), ("Columbia", "F"),
            ("Centa", "F"), ("Voyager", "M"), ("Meridian", "F"), ("Horizon", "U"), ("Tolimann", "M"), ("Proxima", "F"), ("Launch", "M"),
            ("Sunny", "F"), ("Northe", "F"), ("Farshore", "U"), ("Halfway", "M")],
 "balance_virtues": [("Constance", "F"), ("Verity", "F"), ("Patience", "F"), ("Prudence", "F"), ("Temperance", "F"), ("Mercy", "F"),
                     ("Honor", "U"), ("Clement", "M"), ("Amity", "F"), ("Concord", "U"), ("Harmony", "F"), ("Unity", "F"), ("Felicity", "F"),
                     ("Justice", "U"), ("Faith", "F"), ("Hope", "F"), ("Grace", "F"), ("Joy", "F"), ("Serenity", "F"), ("Steady", "M"),
                     ("Even", "U"), ("Keeping", "F"), ("Temper", "M"), ("Thrift", "U"), ("Share", "F"), ("Welcome", "F"), ("Tending", "F")],
 "birds_plants": [("Wren", "F"), ("Lark", "F"), ("Robin", "U"), ("Jay", "M"), ("Finch", "M"), ("Sparrow", "F"), ("Starling", "U"),
                  ("Swallow", "F"), ("Merle", "M"), ("Kestrel", "U"), ("Clover", "F"), ("Juniper", "F"), ("Hazel", "F"), ("Rowan", "U"),
                  ("Laurel", "F"), ("Fern", "F"), ("Sorrel", "U"), ("Yarrow", "F"), ("Tansy", "F"), ("Briar", "U"), ("Alder", "M"),
                  ("Hawthorn", "M"), ("Brook", "F"), ("River", "U"), ("Rain", "F"), ("Marina", "F"), ("Harbor", "M"), ("Shore", "U"),
                  ("Bay", "U"), ("Perch", "M"), ("Walleye", "M"), ("Cherry", "F"), ("Maple", "F"), ("Sumac", "M"), ("Trillium", "F")],
 "station_life": [("Tender", "M"), ("Spinner", "M"), ("Draw", "M"), ("Commons", "M"), ("Keeper", "M"), ("Sunline", "F"), ("Linna", "F"),
                  ("Bowen", "M"), ("Sterne", "M"), ("Crofter", "M"), ("Return", "F"), ("Steward", "M"), ("Welland", "M"), ("Lockie", "M")],
}
# weights of the station's own names by source (the plainest the commonest)
STATION_W = {"geography": 3.0, "great_lakes_memory": 1.5, "voyage": 1.5, "balance_virtues": 2.5, "birds_plants": 3.0, "station_life": 0.3}
# some coined names are loved, most are ordinary, a few are the oddities one family in a thousand uses
STATION_RARITY = {**{n: 0.06 for n in "Walleye Perch Otter Thrift Draw Commons Tender Spinner Keeper Steward Return Share Welcome Tending Keeping Temper Even Halfway Launch Voyager Farshore Northe Proxima Centa Tolimann Chicago Cuyahoga Superior Tole Sumac Crofter Lockie Sunline Linna Victory Sauk".split()},
                  **{n: 0.25 for n in "Brightwater Bellhaven Kessler Loomis Pruett Dunmore Tamarack Fenwick Harrow Solana Marlowe Brannock Kettle Plum Sedge Mackinac Muskegon Saginaw Sandusky Cleveland Ontario Ottawa Welland Sterne Bowen Columbia Sol Rigel Concord Justice Unity Steady Honor".split()},
                  "Carrow": 0.5, "Maumee": 0.5, "Huron": 0.6, "Tamsin": 3.0, "Linden": 1.4, "Hesper": 1.2, "Wren": 1.5, "Hazel": 1.5, "Juniper": 1.3, "Clover": 1.2}

# Given names aboard: the mix of pools by birth cohort (heritage is scaled per family in the engine).
COHORTS = [
    # from, to, mix (the station's own names and its heroes' names grow slowly: fashion, not replacement)
    (2180, 2251, "founders (Earth-born)", {"earth_new": 0.42, "earth_old": 0.20, "earth_mid": 0.13, "heritage": 0.25}),
    (2252, 2299, "launch generations", {"earth_new": 0.36, "earth_old": 0.24, "earth_mid": 0.11, "heritage": 0.24, "station": 0.04, "heroes": 0.01}),
    (2300, 2399, "the Filling and Balance", {"earth_new": 0.29, "earth_old": 0.27, "earth_mid": 0.14, "heritage": 0.21, "station": 0.07, "heroes": 0.02}),
    (2400, 2499, "the Settled Age", {"earth_new": 0.25, "earth_old": 0.26, "earth_mid": 0.17, "heritage": 0.19, "station": 0.10, "heroes": 0.03}),
    (2500, 2599, "the Troubles and after", {"earth_new": 0.24, "earth_old": 0.27, "earth_mid": 0.16, "heritage": 0.18, "station": 0.12, "heroes": 0.03}),
    (2600, 2649, "the Long Calm", {"earth_new": 0.25, "earth_old": 0.26, "earth_mid": 0.15, "heritage": 0.17, "station": 0.14, "heroes": 0.03}),
    (2650, 2689, "the present's grandparents", {"earth_new": 0.25, "earth_old": 0.25, "earth_mid": 0.14, "heritage": 0.17, "station": 0.15, "heroes": 0.04}),
    (2690, 2719, "the present's parents", {"earth_new": 0.25, "earth_old": 0.24, "earth_mid": 0.13, "heritage": 0.16, "station": 0.15, "heroes": 0.035, "vogue": 0.035}),
    (2720, 2752, "the present's young", {"earth_new": 0.25, "earth_old": 0.24, "earth_mid": 0.11, "heritage": 0.15, "station": 0.16, "heroes": 0.03, "vogue": 0.06}),
]
# each present-era decade's fashionable names (the vogue pool; a cohort uses the vogue of its decade)
VOGUE = {
    2690: {"F": "Tamsin Erie Hazel Clover Ada Constance Wren Maumee Lumen Opal Birdie Mabel Josefina Priya Nour", "M": "Linden Otis Harbor Huron Clement Mateo Rigel Arlo Brannock Walt Emeka Hugo Ansel"},
    2700: {"F": "Hesper Juniper Verity Tansy Imogen Lucía Maude Zora Linnet Ottilie Freya Mira", "M": "Sedge Rowan Carrow Felix Kestrel Amir Dashiell Bram Teodoro August Nico"},
    2710: {"F": "Solana Clover Amity Lark Isadora Ximena Birdie Tamsin Noor Pearl Winnie", "M": "Heron Tanner Ambrose Alder Emiliano Merle Kwame Otto Cyrus Jasper"},
    2720: {"F": "Wren Hesper Yarrow Celeste Mabel Leila Constance Frida Rosalie Opal Vega", "M": "Linden Sauk Harbor Clement Idris Ezra Rafael Ansel Huron Milo"},
    2730: {"F": "Juniper Erie Sorrel Honor Nia Paloma Ada Tilly Haven Margo", "M": "Kettle Birch Rigel Mateo Otis Kofi Lorne Callum Emil Walt"},
    2740: {"F": "Tamsin Lumen Clover Evangeline Zuri Sofía Maumee Wren Plum Iris Hattie", "M": "Sedge Carrow Huron Teodoro Amari Jasper Linden Ambrose Felix Bram"},
    2750: {"F": "Hesper Constance Ximena Opal Linnet Zora Maeve Tansy Wren Noor", "M": "Voyager Heron Emeka Rafael Otis Alder Clement Cole Arlo Ibrahim"},
}
NICKNAMES = {
    "Katherine": ["Kate", "Katie", "Kit", "Kathy"], "Catherine": ["Cathy", "Cat", "Kate"], "Elizabeth": ["Liz", "Lizzie", "Beth", "Betsy", "Eliza"],
    "Margaret": ["Maggie", "Meg", "Peg", "Greta"], "William": ["Will", "Bill", "Billy", "Liam"], "Robert": ["Rob", "Bob", "Bobby", "Bert"],
    "James": ["Jim", "Jimmy", "Jamie"], "John": ["Jack", "Johnny"], "Richard": ["Rick", "Dick", "Rich"], "Thomas": ["Tom", "Tommy"],
    "Michael": ["Mike", "Mikey", "Mick"], "Joseph": ["Joe", "Joey"], "Charles": ["Charlie", "Chuck", "Chaz"], "Edward": ["Ed", "Eddie", "Ned", "Ted"],
    "Alexander": ["Alex", "Xander", "Sandy"], "Alexandra": ["Alex", "Lexi", "Sandra"], "Benjamin": ["Ben", "Benny"], "Christopher": ["Chris", "Kit"],
    "Daniel": ["Dan", "Danny"], "David": ["Dave", "Davey"], "Elijah": ["Eli", "Lije"], "Gabriel": ["Gabe"], "Jacob": ["Jake"], "Jonathan": ["Jon", "Jonny"],
    "Matthew": ["Matt"], "Nicholas": ["Nick", "Nicky"], "Patrick": ["Pat", "Paddy"], "Samuel": ["Sam", "Sammy"], "Theodore": ["Ted", "Teddy", "Theo"],
    "Anthony": ["Tony"], "Andrew": ["Andy", "Drew"], "Frederick": ["Fred", "Freddie"], "Henry": ["Hank", "Harry"], "Lawrence": ["Larry", "Laurie"],
    "Victoria": ["Vicky", "Tori"], "Rebecca": ["Becky", "Becca"], "Susan": ["Sue", "Susie"], "Patricia": ["Pat", "Patty", "Trish"],
    "Jennifer": ["Jen", "Jenny"], "Jessica": ["Jess", "Jessie"], "Abigail": ["Abby"], "Isabella": ["Bella", "Izzy"], "Josephine": ["Jo", "Josie"],
    "Dorothy": ["Dot", "Dottie"], "Eleanor": ["Ellie", "Nell", "Nora"], "Florence": ["Flo", "Florrie"], "Harriet": ["Hattie"], "Mary": ["Molly", "Polly", "Mae"],
    "Constance": ["Connie"], "Prudence": ["Prue"], "Temperance": ["Tempe"], "Patience": ["Patty"], "Verity": ["Vee"], "Felicity": ["Fliss"],
    "Tamsin": ["Tam", "Tammy"], "Linden": ["Lin", "Denny"], "Juniper": ["June", "Juni"], "Hesper": ["Hess", "Hettie"], "Maumee": ["Mimi"],
    "Brannock": ["Bran"], "Carrow": ["Carr"], "Kettle": ["Ket"], "Harbor": ["Harb"], "Huron": ["Ron"], "Clement": ["Clem"], "Tamarack": ["Tam", "Rack"],
    "Constantine": ["Con"], "Columbia": ["Colly", "Lumbie"], "Sunline": ["Sunny", "Linnie"], "Solana": ["Lana"], "Bellhaven": ["Belle"],
    "Guadalupe": ["Lupe", "Lupita"], "José": ["Pepe", "Chepe"], "Francisco": ["Paco", "Pancho", "Frank"], "Jesús": ["Chuy"], "Alejandro": ["Alex", "Ale"],
    "Guillermo": ["Memo", "Willie"], "Ignacio": ["Nacho"], "Eduardo": ["Lalo", "Eddie"], "Dolores": ["Lola"], "Graciela": ["Chela"], "Rosario": ["Chayo"],
    "Jean": ["Johnny"], "François": ["Frank"], "Geneviève": ["Gen", "Viv"], "Marguerite": ["Margot"], "Muhammad": ["Mo", "Hamoudi"], "Ibrahim": ["Ibby"],
    "Priya": ["Pri"], "Aarav": ["Avi"], "Chidi": ["Chid"], "Oluwaseun": ["Seun"], "Adaeze": ["Ada"], "Ngozi": ["Ngo"],
}


def build():
    rows = load_surnames()
    fw, info = founder_weights(rows)
    snaps = simulate(fw)
    present = snaps[500]
    total = sum(present.values())
    her = {}
    for n in set(present) | set(snaps[100]) | set(snaps[0]):
        her[n] = info.get(n, ({}, "station_coined" if n.title() in COINED_SURNAMES or n in (c.upper() for c in COINED_SURNAMES) else "anglo"))[1]
    surnames = []
    for n, c in present.most_common():
        disp = n.title() if her[n] == "francophone" else title(n)
        if her[n] == "francophone":
            disp = next((q for q in QUEBEC if q.upper() == n), disp)
        if her.get(n) == "station_coined" or n in {x.upper() for x in COINED_SURNAMES}:
            disp = next((x for x in COINED_SURNAMES if x.upper() == n), disp)
        surnames.append([disp, c, her[n], snaps[0].get(n, 0), snaps[100].get(n, 0), snaps[300].get(n, 0)])
    extinct = [[title(n), snaps[0][n], her.get(n, "anglo")] for n, _ in snaps[0].most_common() if n not in present][:4000]
    her_share = Counter()
    for s in surnames:
        her_share[s[2]] += s[1]
    given = load_given()
    heritage = {h: {s: [[nm, round(1e6 / (i + 1) ** 0.8 / sum(1 / (j + 1) ** 0.8 for j in range(len(H[h][s].split()))), 1)]
                        for i, nm in enumerate(H[h][s].split())] for s in ("F", "M")} for h in H}
    station = {"F": [], "M": []}
    for src, lst in STATION.items():
        for nm, sx in lst:
            w = STATION_W[src] * STATION_RARITY.get(nm, 1.0)
            for s in ("F", "M"):
                if sx == s or sx == "U":
                    station[s].append([nm, w * (0.6 if sx == "U" else 1.0), src])
    for s in station:
        tot = sum(x[1] for x in station[s])
        for x in station[s]:
            x[1] = round(x[1] / tot * 1e6, 1)
    vogue = {str(d): {s: [[nm, 1.0] for nm in v[s].split()] for s in ("F", "M")} for d, v in VOGUE.items()}
    out = {
        "_about": "Columbia game bible: names. Surnames (present frequency after 500 years of simulated inheritance, with heritage and "
                  "founder / VY 100 / VY 300 counts), extinct founding surnames, given-name pools and the cohort mixes that combine them. "
                  "Generated by tools/bible/make_names.py from the 2000 US Census surname file and SSA baby names 1880-2017 (public "
                  "domain) plus hand lists. research/bible/02_names.md.",
        "method": {"founders": FOUNDERS, "founder_mix": FOUNDER_MIX, "francophone_share": FRANCO_SHARE, "generations": GENERATIONS,
                   "generation_years": GEN_YEARS, "coined_per_generation": COINED_PER_GEN, "seed": SEED,
                   "surname_rule": "Charter art. 9: a child takes either parent's surname (about 62% the father's, 33% the mother's, 5% a joined or new name)"},
        "surname_columns": ["surname", "bearers_2752", "heritage", "founders_2252", "bearers_VY100", "bearers_VY300"],
        "surnames": surnames,
        "surname_heritage_share_2752": {k: round(v / total, 4) for k, v in her_share.most_common()},
        "extinct_founding_surnames": extinct,
        "given_pools": {**given, **{"heritage_" + h: heritage[h] for h in heritage}, "station": station, "heroes": {"F": [], "M": []}},
        "vogue": vogue,
        "cohorts": [{"from": a, "to": b, "label": lab, "mix": mix} for a, b, lab, mix in COHORTS],
        "nicknames": NICKNAMES,
        "notes": {"indigenous": NOTE_INDIGENOUS,
                  "hand_lists": "Quebec/Acadian surnames, heritage given names, station names, vogue lists and nicknames are hand-built from knowledge, not downloaded.",
                  "heritage_labels": "From the census surname's ethnic shares, then hand lists (South Asian, Southeast Asian, Arab, Hungarian) and ending patterns for the European sub-heritages (a heuristic)."},
    }
    stats = {"surnames_2752": len(surnames), "bearers": total, "founding_surnames": len(snaps[0]), "extinct": len(snaps[0]) - len([n for n in snaps[0] if n in present]),
             "top20": [s[0] for s in surnames[:20]], "heritage": out["surname_heritage_share_2752"]}
    return out, stats


if __name__ == "__main__":
    o, st = build()
    os.makedirs(os.path.join(ROOT, "godot_project", "remake", "bible"), exist_ok=True)
    with open(os.path.join(ROOT, "godot_project", "remake", "bible", "names.json"), "w") as f:
        json.dump(o, f, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(st, ensure_ascii=False, indent=1)[:3000])
