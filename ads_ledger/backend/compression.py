from collections import defaultdict

class SuffixArray:
    """Sorted array of suffix starting positions for fast pattern search."""

    def __init__(self, text):
        self.text = text
        self.array = sorted(range(len(text)), key=lambda i: text[i:])
    # initialize suffix array with sorted suffix positions for all suffixes of the text

    def search(self, pattern):
        left = self._lower_bound(pattern)
        right = self._upper_bound(pattern)
        return sorted(self.array[left:right])
    # find all starting positions of the given pattern using binary search on the suffix array

    def _lower_bound(self, pattern):
        lo, hi = 0, len(self.array)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.text[self.array[mid] :] < pattern:
                lo = mid + 1
            else:
                hi = mid
        return lo
    # find the first suffix array index whose suffix is not less than the pattern

    def _upper_bound(self, pattern):
        lo, hi = 0, len(self.array)
        upper = pattern[:-1] + chr(ord(pattern[-1]) + 1) if pattern else chr(0x10FFFF)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.text[self.array[mid] :] < upper:
                lo = mid + 1
            else:
                hi = mid
        return lo
    # find the first suffix array index whose suffix is greater than the pattern upper bound

# SuffixArray calculates the sorted suffix positions and supports fast substring search using lower and upper bound binary searches.

def burrows_wheeler_transform(text):
    if not text.endswith("$"):
        text += "$"
    sa = SuffixArray(text).array
    bwt = "".join(text[i - 1] if i > 0 else text[-1] for i in sa)
    return bwt, sa
# burrows_wheeler_transform produces the BWT string and suffix array for the given text, appending a terminal marker if needed.


class FMIndex:
    """Searches compressed BWT text by backward search without decompressing."""

    def __init__(self, text):
        self.text = text if text.endswith("$") else text + "$"
        self.bwt, self.suffix_array = burrows_wheeler_transform(self.text)
        self.first_occurrence = {}
        for i, ch in enumerate(sorted(self.bwt)):
            self.first_occurrence.setdefault(ch, i)
        self.occ = []
        counts = defaultdict(int)
        self.occ.append(dict(counts))
        for ch in self.bwt:
            counts[ch] += 1
            self.occ.append(dict(counts))
    # build FM-index tables: BWT string, suffix array, first occurrence map, and occurrence counts

    def rank(self, ch, upto):
        return self.occ[upto].get(ch, 0)
    # count occurrences of a character up to the given position in the BWT string

    def search(self, pattern):
        if not pattern:
            return []
        top, bottom = 0, len(self.bwt)
        for ch in reversed(pattern.lower()):
            if ch not in self.first_occurrence:
                return []
            top = self.first_occurrence[ch] + self.rank(ch, top)
            bottom = self.first_occurrence[ch] + self.rank(ch, bottom)
            if top >= bottom:
                return []
        return sorted(self.suffix_array[top:bottom])
    # perform backward search over the FM-index to find all occurrences of the pattern

# FMIndex builds the FM-index structures and supports backward search over the compressed BWT string for pattern matching.


class WaveletTree:
    """Compact-ish rank/range query tree for numeric ledger values."""

    def __init__(self, data, lo=None, hi=None):
        self.data_len = len(data)
        self.lo = min(data) if lo is None and data else lo
        self.hi = max(data) if hi is None and data else hi
        self.mid = None
        self.bitvector = []
        self.prefix_zeros = [0]
        self.left = None
        self.right = None
        if not data or self.lo == self.hi:
            return
        self.mid = (self.lo + self.hi) // 2
        left_data, right_data = [], []
        zeros = 0
        for value in data:
            bit = 0 if value <= self.mid else 1
            self.bitvector.append(bit)
            if bit == 0:
                zeros += 1
                left_data.append(value)
            else:
                right_data.append(value)
            self.prefix_zeros.append(zeros)
        if left_data:
            self.left = WaveletTree(left_data, self.lo, self.mid)
        if right_data:
            self.right = WaveletTree(right_data, self.mid + 1, self.hi)
    # construct the wavelet tree over the numeric data using a midpoint split and bitvectors

    def rank(self, value, index):
        index = min(index, self.data_len)
        if self.data_len == 0:
            return 0
        if self.lo == self.hi:
            return index if value == self.lo else 0
        if value <= self.mid:
            next_index = self.prefix_zeros[index]
            return self.left.rank(value, next_index) if self.left else 0
        ones_before = index - self.prefix_zeros[index]
        return self.right.rank(value, ones_before) if self.right else 0
    # count how many times a value occurs up to a given index in the wavelet tree sequence

    def range_count(self, low, high, left=0, right=None):
        if right is None:
            right = self.data_len
        if self.data_len == 0 or high < self.lo or low > self.hi or left >= right:
            return 0
        if low <= self.lo and self.hi <= high:
            return right - left
        left_zeros = self.prefix_zeros[left]
        right_zeros = self.prefix_zeros[right]
        total = 0
        if self.left:
            total += self.left.range_count(low, high, left_zeros, right_zeros)
        if self.right:
            total += self.right.range_count(low, high, left - left_zeros, right - right_zeros)
        return total
    # count values within a given range in the tree using recursive range query logic

# WaveletTree stores numeric values in a tree of bitvectors and supports fast rank and range count queries on those values.


class CompressionEngine:
    def __init__(self):
        self.entries = []
        self.text = ""
        self.fm = None
        self.values = []
        self.wavelet = None
        self.offset_to_entry = []
    # initialize compression engine fields for text indexing and wavelet storage

    def rebuild(self, entries):
        self.entries = entries
        chunks = []
        self.offset_to_entry = []
        cursor = 0
        for entry in entries:
            text = entry["description"].lower()
            chunks.append(text)
            self.offset_to_entry.append((cursor, cursor + len(text), entry))
            cursor += len(text) + 1
        self.text = "\n".join(chunks)
        self.fm = FMIndex(self.text) if self.text else None
        self.values = [int(round(float(entry["value"]))) for entry in entries]
        self.wavelet = WaveletTree(self.values) if self.values else None
    # rebuild internal indexes from entry descriptions and numeric values

    def search_pattern(self, pattern, civilization_id=None):
        if not self.fm or not pattern:
            return []
        positions = self.fm.search(pattern.lower())
        results = []
        seen = set()
        for pos in positions:
            for start, end, entry in self.offset_to_entry:
                if start <= pos < end and entry["id"] not in seen:
                    if civilization_id is None or entry["civilization_id"] == civilization_id:
                        results.append({**entry, "match_position": pos, "snippet": _snippet(entry["description"], pattern)})
                        seen.add(entry["id"])
        return results
    # search descriptions for a pattern and return matching entries with snippet context

    def value_range_query(self, low, high):
        count = self.wavelet.range_count(low, high) if self.wavelet else 0
        rows = [entry for entry in self.entries if low <= float(entry["value"]) <= high]
        return {"count_from_wavelet_tree": count, "entries": rows}
    # query numeric values for entries and count matches using the wavelet tree

    def stats(self):
        return {
            "entries": len(self.entries),
            "text_characters": len(self.text),
            "bwt_characters": len(self.fm.bwt) if self.fm else 0,
            "suffix_array_size": len(self.fm.suffix_array) if self.fm else 0,
            "numeric_values_in_wavelet_tree": len(self.values),
            "compression_note": "Descriptions are indexed through BWT/FM-index; numeric scores are organized in a wavelet tree for rank/range queries.",
        }
    # return statistics about the current indexed entries and compression structures

# CompressionEngine manages entries, builds text index and numeric wavelet tree, and provides search and statistic methods.


def _snippet(text, pattern, radius=80):
    lower = text.lower()
    idx = lower.find(pattern.lower())
    if idx < 0:
        return text[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(pattern) + radius)
    return text[start:end]
# _snippet extracts a text excerpt around the first match of the pattern or returns the beginning of the text if no match is found.
