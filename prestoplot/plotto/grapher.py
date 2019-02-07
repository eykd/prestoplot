import networkx as nx

from ..data import load_xml_path


def get_predicate_id(pred):
    return f'P{pred.get("number")}'


def get_conflict_id(conflict):
    return f'C{conflict.get("id")}'


def get_conflict_id_from_link(clink):
    return f'C{clink.get("ref")}'


def graph_plotto(fp):
    tree = load_xml_path(fp)
    graph = nx.DiGraph()

    for predicate in tree.xpath('//predicate'):
        graph.add_node(get_predicate_id(predicate))

    for conflict in tree.xpath('//conflict'):
        graph.add_node(get_conflict_id(conflict))

    for predicate in tree.xpath('//predicate'):
        pid = get_predicate_id(predicate)
        for clink in predicate.xpath('./conflict-link'):
            graph.add_edge(pid, get_conflict_id_from_link(clink))

    for conflict in tree.xpath('//conflict'):
        cid = get_conflict_id(conflict)
        for clink in conflict.xpath('.//conflict-link'):
            graph.add_edge(cid, get_conflict_id_from_link(clink))

    return graph
