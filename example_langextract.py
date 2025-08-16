"""结构化抽取
"""
import textwrap
import langextract as lx

# 1. Define the prompt and extraction rules
prompt = textwrap.dedent("""\
    这是小学语文练习题。
    一、请提取每一道练习题的以下信息：1.大题题干，以`[一二三四五六七八九十]+、`格式开头；2.题干后的阅读材料或者答题要求；3.小题题干，以`[\d]+\.`或者`[\(（]\d+[）\)]`开头；4.答题语境或者选项。
    二、以精确切分的形式提取每一道练习题的所有文本，不要重叠或重复提取，也不要遗漏任何，也不要改写仍和内容。
    三、对每一道练习题给出知识点标签，如:识字；写字；拼音；词语；句子；阅读；习作；口语交际；古诗文；综合。""")

# 2. Provide a high-quality example to guide the model
examples = [
    lx.data.ExampleData(
        text="""\
一、读句子、根据拼音写字词。
                qín shēng           huì
   广场上响起了悠扬的        ，人们从四面八方    聚到这里，
    gǎn shòu   měi miào
尽情       这       的音乐。""",
        extractions=[
            lx.data.Extraction(
                extraction_class="大题题干",
                extraction_text="一、读句子、根据拼音写字词。",
                attributes={"形式": "文本"}
            ),
            lx.data.Extraction(
                extraction_class="答题语境或者选项",
                extraction_text="""\
                qín shēng           huì
   广场上响起了悠扬的        ，人们从四面八方    聚到这里，
    gǎn shòu   měi miào
尽情       这       的音乐。""",
                attributes={"形式": "看拼音写字词"}
            ),
        ]
    )
]

# The input text to be processed
input_text = """\
二、根据要求完成练习。
  1.“淙淙、唧哩哩、叽叽喳喳”这些词语都和大自然的声音有关，描写
   雨时我会想到类似的词语：               ；描写动物的叫
   时我会想到类似的词语：
 2.先把下面的短语补充完整，再按要求写句子。
      ）的乐曲                ）的呢喃细语
      ）的音乐会               ）的山中小曲
   你在哪里听到过上面这些声音？用上其中的一个短语，写一段话。"""

# Run the extraction
result = lx.extract(
    text_or_documents=input_text,
    prompt_description=prompt,
    examples=examples,
    model_id="qwen2.5:latest",  # Automatically selects Ollama provider
    model_url="http://localhost:11434",
    fence_output=False,
    use_schema_constraints=False
)
