import collections
import random


class MarkovChainDict(collections.Mapping):
    """A Markov Chain dictionary, for generating random strings.

    Derived from Peter Corbett's CGI random name generator:
    http://www.pick.ucam.org/~ptc24/mchain.html
    """

    def __init__(self, random_obj=None):
        self._dict = collections.defaultdict(list)
        self.random = random_obj if random_obj is not None else random.Random()

    def __getitem__(self, key):
        return self._dict[key]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def add_key(self, prefix, suffix):
        self._dict[prefix].append(suffix)

    def get_suffix(self, prefix):
        return self.random.choice(self[prefix])


class NameGenerator(collections.abc.Iterator):
    """Uses a Markov Chain to generate random names.

    Derived from Peter Corbett's CGI random name generator, with input
    from the ElderLore object-oriented variation.

    http://www.pick.ucam.org/~ptc24/mchain.html
    """

    def __init__(self, source_names, chainlen=2, random_obj=None):
        if 1 > chainlen > 10:
            raise ValueError("Chain length must be between 1 and 10, inclusive")
        self.chainlen = chainlen
        self.random = random
        self.markov = MarkovChainDict(random_obj=random_obj)
        self.read_data(source_names, chainlen)

    def __next__(self):
        return self.get_random_name()

    def read_data(self, names, destroy=False):
        if destroy:
            del self.markov
            self.markov = MarkovChainDict()

        oldnames = []
        chainlen = self.chainlen

        for name in names:
            oldnames.append(name)
            spacer = "".join((" " * chainlen, name))
            name_len = len(name)
            for num in range(name_len):
                self.markov.add_key(
                    spacer[num : num + chainlen], spacer[num + chainlen]
                )
            self.markov.add_key(spacer[name_len : name_len + chainlen], "\n")

    def get_random_name(self, start="", max_length=10):
        """Return a random name.
        """
        prefix = start[-self.chainlen :] or " " * self.chainlen
        name = start
        suffix = ""
        while 1:
            suffix = self.markov.get_suffix(prefix)
            if suffix == "-":
                continue
            elif suffix == "\n" or len(name) == max_length:
                break
            else:
                name = "".join((name, suffix))
                prefix = "".join((prefix[1:], suffix))
        return name
