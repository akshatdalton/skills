# Example: Arc D — Data Lineage / Field Tracing

**When to use:** The question is "why does field X show the wrong value at the output?" — a single field is set somewhere early and surfaces wrong somewhere downstream.

**Technique:** Follow the field forward layer by layer, annotate what value it holds at each assignment, mark the terminal node ✓ or ✗. Show the broken path first, then the fixed path so the delta is a single line.

---

## Real example — `filename` in source citations

**Symptom:** RAG citations show `f16203d2-40c9-4cd5-8397-01342821c8e5.txt` instead of `marketing_strategy_q3.txt`.

### Broken path

```
AgentStore.generate_doc_upload_url(filename="marketing_strategy_q3.txt")
  └── s3.generate_presigned_url(Metadata={"filename": "marketing_strategy_q3.txt"})
        # original filename stored as x-amz-meta-filename on S3 object ← exists here

S3Source._read_object(key="agents/documents/f16203d2-....txt")
  file_name = Path(key).name              →  "f16203d2-....txt"
  s3.download_file(bucket, key, tmp.name) # content only — metadata never read
  Document(title=file_name)               →  "f16203d2-....txt"  ← lost here

BuildSearchOperator._enrich()
  └── c.filename = doc.title              →  "f16203d2-....txt"  ✗

ChunkMetadata(filename="f16203d2-....txt") written to LanceDB

RAGToolProvider.execute_tool()
  └── r.metadata.get("filename")          →  "f16203d2-....txt"  ✗  (surfaces to user)
```

### Fixed path

```
S3Source._read_object(key="agents/documents/f16203d2-....txt")
  head = s3.head_object(Bucket=bucket, Key=key)
  title = head["Metadata"].get("filename") or Path(key).name
                                           →  "marketing_strategy_q3.txt"  ← recovered here
  Document(title=title)                    →  "marketing_strategy_q3.txt"

BuildSearchOperator._enrich()
  └── c.filename = doc.title              →  "marketing_strategy_q3.txt"  ✓

RAGToolProvider.execute_tool()
  └── r.metadata.get("filename")          →  "marketing_strategy_q3.txt"  ✓  (surfaces to user)
```

**The fix touches one line** — the rest of the pipeline is correct. The broken-vs-fixed diff makes that immediately visible.

---

## Format rules

- One indented block per layer, connected with `└──`
- Annotate the assignment: `→ "value"` shows what the field holds after each step
- Comment lines (`#`) explain *why* a step matters, not what it does mechanically
- Mark where the value is **lost** in the broken path (`← lost here`) and where it is **recovered** in the fix (`← recovered here`)
- Terminal ✓ / ✗ at the output node only — not at every intermediate step
- Show broken path first so the reader understands what's wrong before seeing the fix
