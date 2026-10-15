"""Read-only v2 catalog. No legacy quiz is silently swapped during import."""
from content_contract import active_for

class Catalog:
    def __init__(self,data):
        self.data=data;self.records={r['id']:r for r in data['records']}
        if len(self.records)!=len(data['records']):raise ValueError('Duplicate material ID')
    def find(self,learning,translation,level=None):
        if learning==translation:raise ValueError('Languages must differ')
        return [r for r in self.records.values() if r['source_language']==learning
                and (level is None or level in r.get('curriculum_levels',{}).get(learning,[]))
                and active_for(r,translation)]
    def legacy_roundtrip(self):return self.data['legacy_source'],self.data['legacy_content']
