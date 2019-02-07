import json
import yaml

from funcy import memoize
from lxml import etree as ET
from path import Path

PATH = Path(__file__).abspath().dirname()


def load_json_path(fp):
    with open(fp) as fi:
        return json.load(fi)


def load_yaml_path(fp):
    with open(fp) as fi:
        return yaml.load(fi)


def load_xml_path(fp):
    parser = ET.XMLParser(load_dtd=False, no_network=True, recover=True, huge_tree=True)
    with open(fp, encoding='utf-8') as fi:
        return ET.parse(fi, parser=parser)


def get_plotto_data():
    return load_xml_path(PATH / 'plotto.xml')


@memoize
def get_male_names():
    return load_json_path(PATH / 'names_male.json')


@memoize
def get_female_names():
    return load_json_path(PATH / 'names_female.json')
