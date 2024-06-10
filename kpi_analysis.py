# coding=utf-8
import configparser
import io
import json
import sys
import time
import openai
import traceback


def llm_api(message, top_p=0.86):
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('openai', 'api_key')
    base_url = config.get('openai', 'base_url')
    model_name = config.get('openai', 'model_name')
    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    completion = client.chat.completions.create(
        model=model_name,
        messages=message,
        top_p=top_p,
    )
    result = json.loads(completion.model_dump_json())
    return result['choices'][0]['message']['content']


def extract_code_block(code_str):
    lines = code_str.strip().split('\n')
    start_index, end_index = None, None

    for i, line in enumerate(lines):
        if line.strip() == '```python':
            start_index = i
        elif line.strip() == '```':
            end_index = i
            break

    if start_index is not None and end_index is not None and start_index < end_index:
        return '\n'.join(lines[start_index + 1:end_index])
    else:
        return ''


def dealError(received_code, error: Exception, index):
    if index > 5:
        return '[]'
    messages = [{'role': 'user', 'content': "csv文件内容如下：开始时间,粒度,网元ID,小区,成功切换成功率,切换尝试次数,异系统切换成功率,小区RB上行平均干扰电平,小区最大激活UE数\
                2024/3/24 21:00,1 小时,676,1,47,33,83,22,38\
                2024/3/24 21:00,1 小时,676,2,59,96,47,34,25\
                2024/3/24 21:00,1 小时,676,3,61,46,94,17,33\
                2024/3/24 21:00,1 小时,342,1,58,46,58,59,67\
                2024/3/24 21:00,1 小时,342,2,15,95,17,54,28\n\
                我的代码报以下错误，"+str(error) +
                 "请帮我修改我的代码:"+received_code+"注意你需要修改好的返回完整的代码内容"}]
    received_code = llm_api(messages)
    print(received_code)
    print('--------------------------------------------------------')
    received_code = extract_code_block(received_code)
    print(received_code)
    print('--------------------------------------------------------')

    output_capture = io.StringIO()
    try:
        sys.stdout = output_capture
        exec(received_code, globals())
    except Exception as e:
        sys.stdout = sys.__stdout__
        print(e)
        captured_output = dealError(
            received_code, traceback.format_exc(), index+1)
    else:
        captured_output = output_capture.getvalue()
        captured_output = captured_output.rstrip()
    finally:
        sys.stdout = sys.__stdout__
    return captured_output


def process_questions(questions):
    answers = []
    for question in questions:
        print("question"+question["index"]+":"+question['description'])

        messages = [{'role': 'system', 'content': '你需要将有用户问题转换为更加明确的问题，用户的问题通常针对于以下csv文件进行python操作的流程：\
                  开始时间,粒度,网元ID,小区,成功切换成功率,切换尝试次数,异系统切换成功率,小区RB上行平均干扰电平,小区最大激活UE数\
            2024/3/24 21:00,1 小时,676,1,47,33,83,22,38\
            2024/3/24 21:00,1 小时,676,2,59,96,47,34,25\
            2024/3/24 21:00,1 小时,676,3,61,46,94,17,33\
            2024/3/24 21:00,1 小时,342,1,58,46,58,59,67   \
            其中前四个字段是信息，后五个字段是指标，网元ID指的是一个站点，一个站点可能有多个小区，这些小区在不同的时间上可能会重复出现，注意“成功切换成功率”和“异系统切换成功率”的字段区别\
            你的回答需要需要包含以下几个内容：\
            1.用户问题中要求回答的内容是什么，回答一定要在list中，你的返回内容尽可能的简单简洁少数据，如果是时间则需要“yyyy-mm-dd hh:mm:ss”或“%Y/%m/%/d %H:%M:/%S”格式，如果是浮点数则需要保留两位小数，如果是数字则不要返回字符串格式，请在你的回答中明确\
            2.问题中的代词替换为实际的名词\n\
            3.问题中的查找条件是什么\
            4.对于csv文件需要按顺序进行哪些操作，以及是否需要将输出的保留两位小数\
            5.转换后的问题是什么 \
            你不需要给出具体的python代码\
            '},
                    {'role': 'user', 'content': question['description']}]
        llm_description = llm_api(messages, 0.9)
        question['description'] = "原始问题：" + \
            question['description'] + "\n" + llm_description
        print(question['description'])
        print('--------------------------------------------------------')

        messages = [{'role': 'system', 'content': "存在一个csv文件是指标文件，描述了 \
                    小区的各种指标按时序的变化情况，文件中字段网元可以理解为一个基站，一个基站下可能有多个小区，数据按照时间顺序从上到下排列，\
                    csv的第一行包含[开始时间,粒度,网元ID,小区,成功切换成功率,切换尝试次数,异系统切换成功率,小区RB上行平均干扰电平,小区最大激活UE数]，这其中的后五个为指标，前四个并不是指标数据，数据示例如下：\
                    2024/3/24 23:00,1 小时,676,2,80,85,90,33,89 \n\
                    2024/3/24 23:00,1 小时,676,3,84,12,7,25,51 \n\
                    2024/3/24 23:00,1 小时,342,1,11,25,65,67,64\n\
                    2024/3/24 23:00,1 小时,342,2,33,4,91,64,37\n\
                    2024/3/24 23:00,1 小时,342,3,35,37,82,74,44\n\
                    2024/3/25 0:00,1 小时,676,2,3,47,17,81,68\n\
                    2024/3/25 0:00,1 小时,676,3,58,45,66,68,82\n\
                    2024/3/25 0:00,1 小时,342,1,94,81,48,11,17"},
                    {'role': 'user', 'content': question['description']+"重点关注转换后的问题，以及该问题的回答格式和内容应该是什么，然后你需要使用python代码读取csv文件并使用print()函数打印回答，回答是使用[]包裹的list类型，请不要打印多余的回答和文字或数据"}]
        result = llm_api(messages)
        print(result)
        print('--------------------------------------------------------')

        messages.append({'role': 'assistant', 'content': result})
        messages.append({
            'role': 'user', 'content': '重新分析并审视你之前的回答是否正确' + question['description'] + '，你需要让代码需要满足以下要求：\
                1.输出如果是浮点数则保留两位小数，可以使用if isinstance(value, float):判断是否是浮点数\n\
                2.请给出对于问题最简单的回答 \n\
                3.注意你需要读取的csv文件在同级目录下‘kpi.csv’，\n\
                4.你的输出需要是list\n\
                5.如果输出是float类型的，请使用round()函数保留两位小数\n\
                6.不需要打印除了答案以外其他的文字,请一定使用print()函数打印\n \
                7.文件是csv文件是UTF-8格式的\n\
                8.如果输出是时间，则格式类似为：2024-03-25 04:00:00 \n\
                9.只有 “成功切换成功率,切换尝试次数,异系统切换成功率,小区RB上行平均干扰电平,小区最大激活UE数” 是指标，“开始时间,粒度,网元ID,小区”作为信息字段，csv中没有其他字段，注意使用pandas读取的时候，除了开始时间和粒度是字符串，其他都是数字类型 \
                10.使用==做相等判断的时候，注意使用数字而不是字符串！！\n\
                11.使用round()函数时，float类型没有round()函数，需要round(float_nums,2)进行小数保留 \
                如果能用一个值回答请不要使用多个值回答问题，你的答案需要尽可能简单，不要将输出的数字转换为字符串！！'
        })

        received_code = llm_api(messages)
        print(received_code)
        print('--------------------------------------------------------')

        received_code = extract_code_block(received_code)
        print(received_code)
        print('--------------------------------------------------------')

        output_capture = io.StringIO()
        try:
            sys.stdout = output_capture
            exec(received_code, globals())
        except Exception as e:
            sys.stdout = sys.__stdout__
            print(e)
            captured_output = dealError(received_code, e, 0)
        else:
            captured_output = output_capture.getvalue()
            captured_output = captured_output.rstrip()
        finally:
            sys.stdout = sys.__stdout__

        if not (captured_output.startswith('[') and captured_output.endswith(']')):
            # 如果不是，则添加 `[` 和 `]`
            captured_output = f'[{captured_output}]'

        answers.append({
            "index": question["index"],
            "description":  captured_output
        })

        with open("./result1.json", "w", encoding='utf-8') as f:
            json.dump({
                "correct_answer": answers}, f, ensure_ascii=False)
    return answers


if __name__ == '__main__':
    with open("./q.json", 'r', encoding='utf-8') as f:
        question_json = json.load(f)

    result_json = process_questions(question_json["question"])

    # with open("./result.json", "w", encoding='utf-8') as f:
    #     json.dump(result_json, f, ensure_ascii=False)
