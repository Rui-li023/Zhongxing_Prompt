import configparser
import io
import json
import sys
import time
import openai
import traceback


def llm_api(message):
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
        messages = [{'role': 'system', 'content': "你需要编写python代码完成上级给定任务，在一个csv文件中获取信息，并得到任务的答案，该csv文件是一个指标文件，描述了 \
                    小区的各种指标按时序的变化情况，文件中字段网元可以理解为一个基站，一个基站下可能有多个小区，数据按照时间顺序从上到下排列，\
                    csv的字段包含[开始时间,粒度,网元ID,小区,成功切换成功率,切换尝试次数,异系统切换成功率,小区RB上行平均干扰电平,小区最大激活UE数]，这其中的后五个为指标，前四个并不是指标数据，数据格式如下：\
                    2024/3/24 23:00,1 小时,676,2,80,85,90,33,89 \n\
                    2024/3/24 23:00,1 小时,676,3,84,12,7,25,51 \n\
                    2024/3/24 23:00,1 小时,342,1,11,25,65,67,64\n\
                    2024/3/24 23:00,1 小时,342,2,33,4,91,64,37\n\
                    2024/3/24 23:00,1 小时,342,3,35,37,82,74,44\n\
                    2024/3/24 23:00,1 小时,856,1,89,84,57,100,61\n\
                    2024/3/24 23:00,1 小时,856,3,68,26,73,57,41\n\
                    2024/3/25 0:00,1 小时,676,1,95,89,29,35,99\n\
                    2024/3/25 0:00,1 小时,676,2,3,47,17,81,68\n\
                    2024/3/25 0:00,1 小时,676,3,58,45,66,68,82\n\
                    2024/3/25 0:00,1 小时,342,1,94,81,48,11,17"},     {'role': 'user', 'content': "你需要使用python代码读取csv文件并使用print打印以下问题的最简单结果：“"+question['description']+"”，请不要给出和打印多余的回答和内容"}]
        result = llm_api(messages)
        print(result)
        print('--------------------------------------------------------')

        messages.append({'role': 'assistant', 'content': result})
        messages.append({
            'role': 'user', 'content': '重新理解问题：' + question['description'] + '，请总结上面的回答并修改代码可能存在的错误，需要满足以下要求：\
                1.给出简介的python代码，\n\
                2.通常来说你的回答只有一个数字、日期或者求一个值、或者一个字段名， \n\
                3.注意你需要读取的csv文件的文件名叫‘kpi.csv’，在同级目录下\n\
                4.你的输出需要是[]包裹的形式\n\
                5.如果输出是float类型的则保留两位小数\n\
                6.不需要打印除了答案以外其他的文字\n \
                7.文件是csv文件是UTF-8格式的\n\
                8.如果输出是时间，则格式类似为：2024-03-25 04:00:00 '
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
