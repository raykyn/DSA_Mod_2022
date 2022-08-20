#!/usr/bin/env python3

"""
Read xlsx and output all files needed for the mod (at the right paths later)
/map_data/definition.csv DONE
/common/landed_titles/ DONE
/history/provinces/[kingdom].txt DONE
/common/province_terrain/00_province_terrain.txt DONE
/history/titles/[kingdom].txt DONE
(optional) /localization/[language]/
"""

from collections import defaultdict
import csv
from typing import DefaultDict
#import numpy as np
import pandas as pd


MASTERSHEET = "Mastersheet_DSA.xlsx"
LOCALIZATION_DICT = {}


class Title(object):
    def __init__(self, name, rank):
        self.name = name  # for localization
        self.code_name = convert_name(name, rank)
        self.liege = None
        self.vassals = []
        self.rank = rank
        self.color = None
        self.province_id = None
        self.type = None
        self.history = []
        self.capital = None  # set it specifically for titular titles
        self.landless = None
        self.culture = None
        self.religion = None

    def get_culture(self):
        if self.culture is None:
            return self.liege.get_culture()
        else:
            return self.culture

    def get_religion(self):
        if self.religion is None:
            return self.liege.get_religion()
        else:
            return self.religion

    def get_capital(self):
        if self.capital is not None:
            return self.capital
        current = self
        while(current.rank != "c_"):
            if len(current.vassals):
                current = current.vassals[0]
            else:
                print("No capital found for {}".format(self))
                return None
        return current.code_name

    def get_color(self):
        if self.color is not None:
            return self.color
        else:
            current = self
            while(current.rank != "b_"):
                if len(current.vassals):
                    current = current.vassals[0]
                elif self.capital is not None:
                    return (0, 0, 0)  # TODO: Somehow pass the dictionary containing all titles to each title object so we can fetch the capital
                else:
                    return (0, 0, 0)
            return current.color

    def get_all_baronies(self):
        baronies = []
        for vassal in self.vassals:
            if vassal.rank == "b_":
                baronies.append(vassal)
            else:
                baronies.extend(vassal.get_all_baronies())
        return baronies

    def __str__(self):
        return self.code_name

    def __repr__(self):
        return self.code_name


def convert_name(name, rank=None):
    # lowercase
    name = name.lower()

    # remove umlaute
    name = name.replace("ä", "ae")
    name = name.replace("ö", "oe")
    name = name.replace("ü", "ue")
    name = name.replace("û", "u")
    name = name.replace("î", "i")
    name = name.replace("é", "e")

    # remove or change special signs
    name = name.replace(".", "")
    name = name.replace("-", "_")

    # remove white spaces
    name = name.replace(" ", "_")

    # add rank prefix
    if rank is not None:
        name = rank + name

    return name


def write_province_definition():
    barony_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Baronies", 
        index_col=0,
    )
    with open("./map_data/definition.csv", mode="w", encoding="ansi") as out:
        out.write("0;0;0;0;x;x;\n")
        for index, row in barony_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            out.write("{};{};{};{};{};x;\n".format(
                str(int(index)),
                int(row["Red"]),
                int(row["Green"]),
                int(row["Blue"]),
                convert_name(row["name"], "b_")
            ))
    with open("./common/province_terrain/00_province_terrain.txt", mode="w", encoding="utf-8-sig") as out:
        out.write("default=plains\n")
        for index, row in barony_sheet.iterrows():
            if pd.isnull(row["name"]):
                continue
            out.write("{0}={1}\n".format(index, row["terrain"]))

def add_hierarchy_level(sheetname, rank, liegerank, liegelist):
    kingdom_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name=sheetname, 
        index_col=0,
    )
    kingdom_level_titles = {}
    for index, row in kingdom_sheet.iterrows():
        if pd.isnull(row["name"]):
            continue
        new_title = Title(row["name"], rank)

        if rank == "b_":
            new_title.color = (
                int(row["Red"]),
                int(row["Green"]),
                int(row["Blue"])
            )
            new_title.province_id = index
            new_title.type = row["type"]
        elif rank == "c_":
            new_title.culture = row["culture"]
            new_title.religion = row["religion"]
            read_title_history_from_file(row["history"], new_title)
        else:
            if rank != "c_":
                if not pd.isnull(row["capital"]):
                    new_title.capital = convert_name(row["capital"], "c_")
            read_title_history_from_file(row["history"], new_title)

        if "landless" in row and not pd.isnull(row["landless"]) and row["landless"] == "yes":
            new_title.landless = True

        if not pd.isnull(row[liegerank]):
            liegelist[row[liegerank]].vassals.append(new_title)
            new_title.liege = liegelist[row[liegerank]]
        else:
            liegelist[row["name"]] = new_title
        kingdom_level_titles[row["name"]] = new_title

    return kingdom_level_titles


def read_title_history_from_file(text, title):
    if pd.isnull(text):
        return
    for event in text.split(";"):
        if not event:
            continue
        ev, target, date = event.split(":")
        for e in ev.split(","):
            title.history.append((date, e, target))


def create_title_hierarchy():
    empire_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Empires", 
        index_col=0,
    )
    top_level_titles = {}
    for index, row in empire_sheet.iterrows():
        top_level_titles[row["name"]] = Title(row["name"], "e_")
        read_title_history_from_file(row["history"], top_level_titles[row["name"]])
    
    kingdom_titles = add_hierarchy_level("Kingdoms", "k_", "empire", top_level_titles)
    duchy_titles = add_hierarchy_level("Duchies", "d_", "kingdom", kingdom_titles)
    county_titles = add_hierarchy_level("Counties", "c_", "duchy", duchy_titles)
    add_hierarchy_level("Baronies", "b_", "county", county_titles)

    return top_level_titles

    
def write_landed_titles(top_level_titles):

    def write_start(code_name, capital_color, indent=0):
        indent = indent * " "
        line1 = indent + "{} = {{\n".format(code_name)
        line2 = indent + "    color = {{ {0} {1} {2} }}\n".format(
            capital_color[0],
            capital_color[1],
            capital_color[2]
        )
        line3 = indent + "    color2 = { 255 255 255 }\n"
        return line1+line2+line3

    def write_capital(capital_code_name, indent=0):
        if capital_code_name is not None:
            indent = indent * " "
            return indent + "    capital = {0}\n\n".format(capital_code_name)
        else:
            return ""

    def write_vassals(outfile, vassals, indent):
        for vassal in vassals:
            outfile.write(write_start(vassal.code_name, vassal.get_color(), indent=indent))
            
            if vassal.landless:
                outfile.write("    landless = yes\n")

            if vassal.rank != "c_" and vassal.rank != "b_":
                outfile.write(write_capital(vassal.get_capital(), indent=indent))
            elif vassal.rank == "b_":
                outfile.write(indent*" " + "    province = {0}\n".format(vassal.province_id))
            else:
                outfile.write("\n")

            write_vassals(outfile, vassal.vassals, indent+4)

            outfile.write(indent*" " + "}\n\n")

    outfile = open("./common/landed_titles/00_landed_titles.txt", mode="w", encoding="utf-8-sig")

    for title, title_obj in top_level_titles.items():
        outfile.write(write_start(title_obj.code_name, title_obj.get_color()))

        if title_obj.landless:
            outfile.write("    landless = yes\n")

        outfile.write(write_capital(title_obj.get_capital()))

        write_vassals(outfile, title_obj.vassals, 4)

        outfile.write("}\n\n")

    outfile.close()


def write_province_history(top_level_titles):
    kingdoms = []
    for title, title_obj in top_level_titles.items():
        if title_obj.rank == "k_":
            kingdoms.append(title_obj)
        for vassal in title_obj.vassals:
            if vassal.rank == "k_":
                kingdoms.append(vassal)

    for kingdom in kingdoms:
        baronies = kingdom.get_all_baronies()
        with open("./history/provinces/{0}.txt".format(kingdom.code_name), mode="w", encoding="utf-8-sig") as out:
            for barony in baronies:
                out.write("# {0} - {1}\n".format(barony.province_id, barony.name))
                out.write("{0} = {{\n\n".format(barony.province_id))
                out.write("    culture = {0}\n".format(barony.get_culture()))
                out.write("    religion = {0}\n".format(barony.get_religion()))
                if barony.type == "B":
                    holding_type = "castle_holding"
                elif barony.type == "T":
                    holding_type = "church_holding"
                elif barony.type == "C":
                    holding_type = "city_holding"
                    # TODO: Add tribal when it's implemented
                else:
                    print("ERROR: Unknown holding type {0}!".format(barony.type))
                out.write("    holding = {0}\n\n".format(holding_type))
                out.write("}\n\n")


def write_title_history_recursive(liege, out):
    for vassal in liege.vassals:
        out.write("{0} = {{\n".format(vassal.code_name))
        # set dejure liege as default liege
        out.write(write_history_block("1", "liege", vassal.liege.code_name))
        for date, event, target in sorted(vassal.history, key=lambda x: int(x[0].split(".")[0])):
            out.write(write_history_block(date, event, target))
        out.write("}\n\n")
        write_title_history_recursive(vassal, out)


def write_title_history(top_level_titles):
    others = []
    kingdoms = []
    for title, title_obj in top_level_titles.items():
        if title_obj.rank == "k_":
            kingdoms.append(title_obj)
        else:
            others.append(title_obj)
        for vassal in title_obj.vassals:
            if vassal.rank == "k_":
                kingdoms.append(vassal)

    out = open("./history/titles/00_other_titles.txt", mode="w", encoding="utf-8-sig")
    for empire in others:
        out.write("{0} = {{\n".format(empire.code_name))
        for date, event, target in sorted(empire.history, key=lambda x: int(x[0])):
            out.write(write_history_block(date, event, target))
        out.write("}\n\n")
    out.close()
        

    for kingdom in kingdoms:
        out = open("./history/titles/000_{0}.txt".format(kingdom.code_name), mode="w", encoding="utf-8-sig")

        out.write("{0} = {{\n".format(kingdom.code_name))
        if kingdom.liege is not None:
            out.write(write_history_block("1", "liege", kingdom.liege.code_name))
        for date, event, target in sorted(kingdom.history, key=lambda x: int(x[0])):
            out.write(write_history_block(date, event, target))
        out.write("}\n\n")

        write_title_history_recursive(kingdom, out)

        out.close()


def flatten_hierarchy(hierarchy):
    def iterate_vassals(title, out_dict):
        for vassal in title.vassals:
            out_dict[vassal.code_name] = vassal
            iterate_vassals(vassal, out_dict)

    out_dict = {}
    for title, title_obj in hierarchy.items():
        out_dict[title_obj.code_name] = title_obj
        iterate_vassals(title_obj, out_dict)
    return out_dict


def write_history_block(date, event, target, indent=4):
    try:
        date = str(int(date)).lstrip("0")
    except:
        pass  # 984.1.1 will throw an exception bc it cant be put into an int
    if len(date) <= 4:  # maybe sometimes i'll give more specific dates
        date = "{0}.1.1".format(date)
    line1 = indent*" " + "{0} = {{\n".format(date)
    line2 = indent*" " + "    {0} = {1}\n".format(event, target)
    line3 = indent*" " + "}\n"
    return line1 + line2 + line3


def add_titles_to_localization(titles):
    for title, title_obj in titles.items():
        LOCALIZATION_DICT[title] = title_obj.name

def write_character_history(top_level_titles, dynasty_list):
    all_titles_dict = flatten_hierarchy(top_level_titles)
    add_titles_to_localization(all_titles_dict)
    
    character_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Characters", 
        index_col=0,
    )
    collect_names = set()
    # TODO: Do one file per culture
    out = open("./history/characters/000_test_characters.txt", mode="w", encoding="utf-8-sig")
    for index, row in character_sheet.iterrows():
        if pd.isnull(row["name"]):
            continue
        out.write("{0} = {{\n".format(int(index)))

        if row["culture"] == "garetian" and row["female"] == "yes":
            for n in row["name"].split():
                collect_names.add(n)

        out.write('    name = "{0}"\n'.format(row["name"]))
        if int(row["dynasty"]) not in dynasty_list and int(row["dynasty"]) != 0:
            print("WARNING! Dynasty id {0} not found!".format(int(row["dynasty"])))
        elif int(row["dynasty"]) != 0:
            out.write("    dynasty_house = house_{0}\n".format(int(row["dynasty"])))
        out.write("    female = {0}\n".format(row["female"]))
        # religion and culture
        out.write("    culture = {0}\n".format(row["culture"]))
        if not pd.isnull(row["religion"]):
            out.write("    religion = {0}\n".format(row["religion"]))
        else:
            out.write("    religion = {0}\n".format("testism"))
        # family
        if not pd.isnull(row["father"]):
            out.write("    father = {0}\n".format(int(row["father"])))
        if not pd.isnull(row["mother"]):
            out.write("    mother = {0}\n".format(int(row["mother"])))
        # TODO: attributes and traits
        # out.write("    disallow_random_traits = yes\n")
        # character history
        out.write(write_history_block(row["birth"], "birth", "yes"))
        # TODO: add_spouses, employers, etc.
        # give title history info to titles
        if not pd.isnull(row["history"]):
            events = row["history"].split(";")
            for event_date in events:
                event_date = event_date.split(":")
                for event in event_date[0].split(","):  # multiple events same day
                    if event in all_titles_dict:
                        all_titles_dict[event].history.append((event_date[1], "holder", int(index)))
                    elif len(event_date) > 2:
                        out.write(write_history_block(event_date[2], event, event_date[1]))
                    else:
                        print("Error: Encountered unknown character history event: {0}".format(event))

        out.write(write_history_block(row["death"], "death", "yes"))
        
        out.write("}\n\n")

    # print(",".join(list(collect_names)))

    out.close()


def write_dynasties():
    out_dyn = open("./common/dynasties/00_dynasties.txt", mode="w", encoding="utf-8-sig")
    out_house = open("./common/dynasty_houses/00_dynasty_houses.txt", mode="w", encoding="utf-8-sig")
    dynasty_list = set()
    dynasty_dict = {}  # dynasty to index

    dynasty_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="Dynasty", 
        index_col=0,
    )
    for index, row in dynasty_sheet.iterrows():
        if pd.isnull(row["dynasty"]):
            continue
        if not pd.isnull(row["prefix"]):
            prefix = '    prefix = dynnp_{0}\n'.format(row["prefix"])
        else:
            prefix = ""
        if row["dynasty"] in dynasty_dict:
            dyn_index = dynasty_dict[row["dynasty"]]
        else:
            dynasty_dict[row["dynasty"]] = index
            dyn_index = index
            out_dyn.write('{0} = {{\n'.format(dyn_index)+prefix)
            out_dyn.write('    name = dynn_{0}\n'.format(convert_name(row["dynasty"])))
            out_dyn.write('    culture = {0}\n'.format(row["culture"]))
            out_dyn.write("}\n")

            LOCALIZATION_DICT['dynn_{0}'.format(convert_name(row["dynasty"]))] = row["dynasty"]

        # TODO: Give houses different indices to dynasties or they'll get the same Coat of Arms
        # for example prefixed with house_
        out_house.write('house_{0} = {{\n'.format(index)+prefix)
        out_house.write('    name = dynn_{0}\n'.format(convert_name(row["house"])))
        out_house.write('    dynasty = {0}\n'.format(dyn_index))
        out_house.write("}\n")

        LOCALIZATION_DICT['dynn_{0}'.format(convert_name(row["house"]))] = row["house"]

        dynasty_list.add(index)

    out_dyn.close()
    out_house.close()

    return dynasty_list


def write_localization():
    with open("./localization/english/dsa_mod_l_english.yml", mode="w", encoding="utf-8-sig") as out:
        out.write("l_english:\n")
        for key, value in LOCALIZATION_DICT.items():
            out.write(' {0}:0 "{1}"\n'.format(key, value))


def write_coa():
    coa_sheet: pd.DataFrame = pd.read_excel(
        MASTERSHEET, 
        sheet_name="COA", 
        index_col=0,
    )
    out = open("./common/coat_of_arms/coat_of_arms/00_mixed_coa.txt", mode="w", encoding="utf-8-sig")
    for index, row in coa_sheet.iterrows():
        out.write("{0} = {{\n".format(index))
        out.write(row["code"])
        out.write("\n}\n")

    out.close()
    


def main():
    write_province_definition()
    top_level_titles = create_title_hierarchy()
    write_landed_titles(top_level_titles)
    write_province_history(top_level_titles)
    dynasty_list = write_dynasties()
    write_character_history(top_level_titles, dynasty_list)
    write_title_history(top_level_titles)
    write_coa()

    write_localization()
    


if __name__ == "__main__":
    main()