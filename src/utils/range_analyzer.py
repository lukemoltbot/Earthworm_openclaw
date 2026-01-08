"""
Range analyzer for lithology settings - identifies gaps in gamma and density ranges
"""

class RangeAnalyzer:
    """Analyzes lithology ranges to identify coverage gaps"""

    def __init__(self):
        # Global range limits as specified by user
        self.gamma_min_limit = 0
        self.gamma_max_limit = 300
        self.density_min_limit = 0
        self.density_max_limit = 4

    def analyze_gamma_ranges(self, lithology_rules):
        """Analyze gamma ranges and return covered segments and gaps"""
        return self._analyze_ranges(lithology_rules,
                                   'gamma_min', 'gamma_max',
                                   self.gamma_min_limit, self.gamma_max_limit)

    def analyze_density_ranges(self, lithology_rules):
        """Analyze density ranges and return covered segments and gaps"""
        return self._analyze_ranges(lithology_rules,
                                   'density_min', 'density_max',
                                   self.density_min_limit, self.density_max_limit)

    def analyze_gamma_ranges_with_overlaps(self, lithology_rules):
        """Analyze gamma ranges preserving overlapping ranges for visualization"""
        return self._analyze_ranges_with_overlaps(lithology_rules,
                                                 'gamma_min', 'gamma_max',
                                                 self.gamma_min_limit, self.gamma_max_limit)

    def analyze_density_ranges_with_overlaps(self, lithology_rules):
        """Analyze density ranges preserving overlapping ranges for visualization"""
        return self._analyze_ranges_with_overlaps(lithology_rules,
                                                 'density_min', 'density_max',
                                                 self.density_min_limit, self.density_max_limit)

    def _analyze_ranges(self, lithology_rules, min_key, max_key, global_min, global_max):
        """
        Generic range analysis for a given parameter type
        Returns: (covered_segments, gaps)
        """
        if not lithology_rules:
            return [], [(global_min, global_max)]

        # Extract valid ranges from rules
        ranges = []
        for rule in lithology_rules:
            r_min = rule.get(min_key)
            r_max = rule.get(max_key)

            # Skip invalid ranges
            if r_min is None or r_max is None or r_min >= r_max:
                continue

            ranges.append({
                'min': r_min,
                'max': r_max,
                'name': rule.get('name', 'Unknown'),
                'code': rule.get('code', ''),
                'background_color': rule.get('background_color', '#FFFFFF')
            })

        if not ranges:
            return [], [(global_min, global_max)]

        # Sort ranges by min value
        ranges.sort(key=lambda x: x['min'])

        # Merge overlapping ranges
        merged_ranges = self._merge_overlapping_ranges(ranges)

        # Find gaps within the global range
        gaps = self._find_gaps(merged_ranges, global_min, global_max)

        return merged_ranges, gaps

    def _merge_overlapping_ranges(self, ranges):
        """Merge overlapping or adjacent ranges"""
        if not ranges:
            return []

        merged = [ranges[0].copy()]

        for current in ranges[1:]:
            last = merged[-1]

            # If current range overlaps or touches the last merged range
            if current['min'] <= last['max']:
                # Extend the last merged range
                last['max'] = max(last['max'], current['max'])
                # If names are different, combine them
                if last['name'] != current['name']:
                    last['name'] = f"{last['name']}/{current['name']}"

                # Combine codes if different
                if last['code'] != current['code']:
                    last['code'] = f"{last['code']}+{current['code']}"
            else:
                merged.append(current.copy())

        return merged

    def _find_gaps(self, covered_ranges, global_min, global_max):
        """Find gaps between covered ranges within global limits"""
        if not covered_ranges:
            return [(global_min, global_max)]

        gaps = []

        # Gap from global_min to first range
        if covered_ranges[0]['min'] > global_min:
            gaps.append((global_min, covered_ranges[0]['min']))

        # Gaps between ranges
        for i in range(len(covered_ranges) - 1):
            gap_start = covered_ranges[i]['max']
            gap_end = covered_ranges[i + 1]['min']
            if gap_start < gap_end:
                gaps.append((gap_start, gap_end))

        # Gap from last range to global_max
        if covered_ranges[-1]['max'] < global_max:
            gaps.append((covered_ranges[-1]['max'], global_max))

        return gaps

    def _analyze_ranges_with_overlaps(self, lithology_rules, min_key, max_key, global_min, global_max):
        """
        Generic range analysis preserving overlapping ranges for visualization
        Returns: (preserved_ranges, gaps)
        """
        if not lithology_rules:
            return [], [(global_min, global_max)]

        # Extract valid ranges from rules
        ranges = []
        for rule in lithology_rules:
            r_min = rule.get(min_key)
            r_max = rule.get(max_key)

            # Skip invalid ranges
            if r_min is None or r_max is None or r_min >= r_max:
                continue

            ranges.append({
                'min': r_min,
                'max': r_max,
                'name': rule.get('name', 'Unknown'),
                'code': rule.get('code', ''),
                'background_color': rule.get('background_color', '#FFFFFF')
            })

        if not ranges:
            return [], [(global_min, global_max)]

        # Sort ranges by min value
        ranges.sort(key=lambda x: x['min'])

        # DON'T merge overlapping ranges - preserve them for layered visualization
        preserved_ranges = ranges

        # Find gaps using the merged logic (for gap identification only)
        merged_ranges, gaps = self._analyze_ranges(lithology_rules, min_key, max_key, global_min, global_max)

        return preserved_ranges, gaps

    def get_overlap_summary_text(self, overlapping_ranges):
        """Generate human-readable summary of overlapping ranges"""
        if not overlapping_ranges:
            return "No overlapping ranges found"
        elif len(overlapping_ranges) == 1:
            return f"Single range: {overlapping_ranges[0]['name']} ({overlapping_ranges[0]['min']:.1f} - {overlapping_ranges[0]['max']:.1f})"
        else:
            overlap_texts = [f"{r['name']} ({r['min']:.1f}-{r['max']:.1f})" for r in overlapping_ranges]
            return f"Overlapping lithologies: {', '.join(overlap_texts)}"

    def get_gap_summary_text(self, gaps):
        """Generate human-readable summary of gaps"""
        if not gaps:
            return "No gaps found - full coverage"
        elif len(gaps) == 1:
            return f"Gap: {gaps[0][0]:.1f} - {gaps[0][1]:.1f}"
        else:
            gap_texts = [f"{gap[0]:.1f}-{gap[1]:.1f}" for gap in gaps]
            return f"Gaps: {', '.join(gap_texts)}"
