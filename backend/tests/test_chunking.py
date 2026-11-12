from app.ingest.chunking import chunk_by_headings, chunk_by_length, pack_blocks, split_blocks

DOC = """# Postgres 인덱스

인덱스는 조회를 빠르게 하는 별도 자료구조다. 쓰기 비용이 늘어난다.

## B-tree

기본 인덱스. 범위 검색과 정렬에 강하다.

### 언제 쓰나

등호와 범위 조건이 많은 컬럼에 쓴다.

## GIN

배열, JSONB, 전문 검색처럼 값 하나에 키가 여러 개인 경우에 쓴다.

```sql
# 이건 코드 안의 주석이지 제목이 아니다
CREATE INDEX ON docs USING gin (tags);
```
"""


def test_heading_paths_follow_hierarchy():
    drafts = chunk_by_headings(DOC, title="Postgres 인덱스", min_chars=0)
    paths = [d.heading_path for d in drafts]
    assert paths == [
        "Postgres 인덱스",
        "Postgres 인덱스 > B-tree",
        "Postgres 인덱스 > B-tree > 언제 쓰나",
        "Postgres 인덱스 > GIN",
    ]


def test_hash_inside_code_fence_is_not_a_heading():
    drafts = chunk_by_headings(DOC, title="Postgres 인덱스", min_chars=0)
    gin = drafts[-1]
    assert "# 이건 코드 안의 주석" in gin.text
    assert "CREATE INDEX" in gin.text


def test_title_not_duplicated_when_h1_matches():
    drafts = chunk_by_headings("# 제목\n\n본문입니다 본문입니다.", title="제목", min_chars=0)
    assert drafts[0].heading_path == "제목"


def test_long_section_is_split_under_max_chars():
    paragraphs = "\n\n".join(f"문단 {i} " + "가나다라마바사 " * 20 for i in range(10))
    drafts = chunk_by_headings(f"# T\n\n## 긴 섹션\n\n{paragraphs}", title="T", max_chars=400)
    assert len(drafts) > 1
    assert all(len(d.text) <= 400 for d in drafts)
    assert all(d.heading_path == "T > 긴 섹션" for d in drafts)


def test_oversize_single_paragraph_is_hard_split():
    sentence = "이것은 아주 긴 문장입니다. " * 100
    pieces = pack_blocks([sentence], max_chars=200)
    assert len(pieces) > 1
    assert all(len(p) <= 200 for p in pieces)


def test_code_block_is_never_split():
    code = "```python\n" + "\n".join(f"x{i} = {i}" for i in range(200)) + "\n```"
    blocks = split_blocks(f"앞 문단\n\n{code}\n\n뒤 문단")
    assert blocks[1] == code
    assert code in pack_blocks(blocks, max_chars=100)


def test_tiny_chunk_is_merged_into_next_in_same_section():
    body = "# T\n\n## S\n\n짧음\n\n" + "충분히 긴 문단입니다. " * 10
    drafts = chunk_by_headings(body, title="T", max_chars=40, min_chars=10)
    assert drafts[0].text.startswith("짧음")


def test_embedding_text_includes_heading_context():
    d = chunk_by_headings("## GIN\n\n배열 인덱스 설명입니다.", title="인덱스", min_chars=0)[0]
    assert d.embedding_text().startswith("인덱스 > GIN\n\n")


def test_length_chunking_ignores_heading_structure():
    drafts = chunk_by_length("첫 메모 " * 50 + "\n\n" + "둘째 메모 " * 50, title="m", max_chars=300)
    assert len(drafts) == 2
    assert all(d.heading_path == "m" for d in drafts)
