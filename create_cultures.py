#!/usr/bin/env python3

import pandas as pd


MASTERSHEET = "Cultures.xlsx"


def write_entry_brackets(var, entries):
    entries = ["{} = {}".format(e.split(":")[0], e.split(":")[1]) if ":" in e else e for e in entries]
    entries = " ".join(entries)
    return "{0} = {{ {1} }}\n".format(var, entries)


def write_heritages():
    heritage_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Heritages"
    )
    with open("./common/culture/pillars/01_heritage.txt", mode="w", encoding="utf8") as out:
        for index, row in heritage_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            code = "heritage_" + row["code"]
            entry = write_entry_brackets(code, ["type = heritage"])
            out.write(entry + "\n")


def write_languages():
    lang_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Languages"
    )
    with open("./common/culture/pillars/01_language.txt", mode="w", encoding="utf8") as out:
        for index, row in lang_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            code = "language_" + row["code"]
            out.write("{} = {{".format(code))
            out.write("""
    type = language
	is_shown = {{
		language_is_shown_trigger = {{
			LANGUAGE = {0}
		}}
	}}
	ai_will_do = {{
		value = 10
		if = {{
			limit = {{ has_cultural_pillar = {0} }}
			multiply = 10
		}}
	}}
    """.format(code))

            out.write("color = {}\n".format(row["color"]))

            out.write("}\n\n")


def write_names():
    lang_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Names"
    )
    variables = [
        "pat_grf_name_chance",
	    "mat_grf_name_chance",
	    "father_name_chance",
	    "pat_grm_name_chance",
	    "mat_grm_name_chance",
	    "mother_name_chance"
    ]
    with open("./common/culture/name_lists/00_dsa.txt", mode="w", encoding="utf8") as out:
        for index, row in lang_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            code = "language_" + row["code"]
            out.write("{} = {{\n".format(code))
            male_names = write_entry_brackets("male_names", row["male_names"].split(","))
            female_names = write_entry_brackets("female_names", row["female_names"].split(","))
            out.write("    {}\n".format(male_names))
            out.write("    {}\n".format(female_names))

            if not pd.isnull(row["dynasty_loc_prefix"]):
                out.write('    dynasty_of_location_prefix = "dynnp_{}"\n\n'.format(row["dynasty_loc_prefix"]))

            for var, val in zip(variables, row["inherited_names_chances"].split(",")):
                out.write("    {0} = {1}\n".format(var, val))
            
            out.write("}\n\n")


def write_cultures():
    culture_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Cultures"
    )
    tradition_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Traditions"
    )

    traditions = {}
    for index, row in tradition_sheet.iterrows():
        if pd.isnull(row["name"]):
                continue
        tradlist = []
        for i in range(6):
            field = "tradition_" + str(i+1)
            if pd.isnull(row[field]):
                continue
            tradlist.append(row[field])
        traditions[row["name"]] = tradlist

    with open("./common/culture/cultures/00_dsa.txt", mode="w", encoding="utf8") as out:
        for index, row in culture_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            out.write("{} = {{\n".format(row["code"]))

            colors = write_entry_brackets("color", row["color"].split(","))
            out.write("    " + colors + "\n")

            out.write("    heritage = heritage_{}\n".format(row["heritage"]))
            out.write("    ethos = {}\n".format(row["ethos"]))
            out.write("    language = language_{}\n".format(row["language"]))
            out.write("    martial_custom = {}\n".format(row["martial_custom"]))

            out.write("    {}\n".format(write_entry_brackets("traditions", traditions[row["code"]])))
            
            out.write("    name_list = {}\n\n".format(row["name_list"]))
           
            out.write("    {}".format(write_entry_brackets("coa_gfx", [row["coa_gfx"]])))
            out.write("    {}".format(write_entry_brackets("building_gfx", [row["building_gfx"]])))
            out.write("    {}".format(write_entry_brackets("clothing_gfx", [row["clothing_gfx"]])))
            out.write("    {}\n".format(write_entry_brackets("unit_gfx", [row["unit_gfx"]])))

            ethnicities = write_entry_brackets("ethnicities", row["ethnicities"].split(","))
            out.write("    " + ethnicities)

            out.write("}\n\n")


def main():
    # create heritages
    write_heritages()
    # create languages
    write_languages()
    # create name lists
    write_names()
    # create cultures
    write_cultures()

if __name__ == "__main__":
    main()