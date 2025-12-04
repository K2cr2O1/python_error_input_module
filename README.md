# Python Error Input Module

一个功能强大的Python错误监听和处理模块，支持自动捕获、报告和处理函数执行过程中的异常，提供灵活的配置选项和友好的API接口。

## 功能特性

- 🎯 **装饰器模式**：简单易用的`@error_decorator`装饰器，支持同步和异步函数
- 📋 **错误信息收集**：自动收集详细的错误信息，包括错误类型、消息、堆栈跟踪等
- 🔄 **异常链支持**：完整记录异常链信息，便于追踪错误根源
- 📊 **代码上下文捕获**：可配置捕获错误发生位置的代码片段
- 📝 **局部变量捕获**：支持捕获函数执行时的局部变量值
- 🎨 **高亮代码显示**：提供错误位置的代码高亮功能
- ⚙️ **灵活配置**：支持多种配置选项，满足不同场景需求
- 📡 **自定义处理器**：允许用户定义自己的错误处理逻辑
- 🔀 **异常忽略与传播**：可配置忽略特定异常或向上传播异常
- ⏱️ **时间戳记录**：自动记录错误发生的时间
- 📂 **支持多种函数类型**：兼容普通函数、类方法、静态方法

## 安装方法

直接将`scan_error.py`文件复制到您的项目目录中即可使用。

## 快速开始

### 基本用法

```python
from scan_error import error_decorator

@error_decorator
def divide_numbers(a, b):
    """一个可能会抛出异常的除法函数"""
    return a / b

# 调用函数，错误会被自动捕获并处理
try:
    result = divide_numbers(10, 0)
    print(f"结果: {result}")  # 输出: 结果: ZeroDivisionError
except Exception as e:
    print(f"未被捕获的异常: {e}")
```

### 异步函数支持

```python
import asyncio
from scan_error import error_decorator

@error_decorator
async def async_divide(a, b):
    """异步除法函数"""
    await asyncio.sleep(0.1)
    return a / b

# 异步调用
async def main():
    result = await async_divide(10, 0)
    print(f"结果: {result}")  # 输出: 结果: ZeroDivisionError

asyncio.run(main())
```

## 详细使用指南

### 自定义错误处理器

```python
from scan_error import error_decorator, set_error_handler

def custom_error_handler(error_info):
    """自定义错误处理器"""
    error_data = error_info['error']
    print(f"[自定义处理器] 捕获到错误: {error_data['type']}")
    print(f"错误信息: {error_data['message']}")
    print(f"错误发生时间: {error_data['timestamp']}")

# 设置自定义错误处理器
set_error_handler(custom_error_handler)

@error_decorator
def error_function():
    return 1 / 0

# 调用函数，错误会被自定义处理器处理
error_function()
```

### 高级配置选项

```python
from scan_error import error_decorator

@error_decorator(
    ignore_errors=[ValueError],  # 忽略特定异常类型
    propagate_errors=[TypeError],  # 向上传播特定异常类型
    custom_context={"module": "user_service"},  # 自定义上下文信息
    capture_code_context=True,  # 是否捕获代码上下文
    error_level="ERROR",  # 错误级别：ERROR, WARNING, INFO, DEBUG
    capture_locals=True,  # 是否捕获局部变量
    max_stack_depth=5  # 最大堆栈深度
)
def complex_function(data):
    if not isinstance(data, dict):
        raise TypeError("数据必须是字典类型")
    if "id" not in data:
        raise ValueError("缺少必要字段'id'")
    return data["id"]

# 调用函数
result = complex_function({"name": "test"})  # 输出: ValueError（被忽略）
result = complex_function("not a dict")  # 抛出: TypeError（被传播）
```

### 类方法和静态方法支持

```python
from scan_error import error_decorator

class TestClass:
    @error_decorator
    def instance_method(self, x, y):
        return x / y

    @error_decorator
    @classmethod
    def class_method(cls, x, y):
        return x / y

    @error_decorator
    @staticmethod
    def static_method(x, y):
        return x / y

# 使用方法
test_obj = TestClass()
result1 = test_obj.instance_method(10, 0)  # 捕获到实例方法错误
result2 = TestClass.class_method(20, 0)  # 捕获到类方法错误
result3 = TestClass.static_method(30, 0)  # 捕获到静态方法错误
```

### 手动报告错误

```python
from scan_error import report_error

# 手动报告错误
report_error(
    ValueError,  # 错误类型
    "手动报告的错误",  # 错误原因
    capture_code_context=True,  # 是否捕获代码上下文
    error_level="WARNING",  # 错误级别
    custom_field="自定义字段值"  # 自定义字段
)
```

## API参考

### error_decorator(func=None, **kwargs)

错误监听装饰器，用于捕获并处理函数执行过程中的异常。

#### 参数

- `func`: 可选，需要被装饰的函数
- `ignore_errors`: 可选，要忽略的异常类型列表
- `propagate_errors`: 可选，需要向上传播的异常类型列表
- `custom_context`: 可选，自定义上下文信息字典
- `capture_code_context`: 可选，是否捕获代码上下文，默认为True
- `error_level`: 可选，错误信息级别 (ERROR, WARNING, INFO, DEBUG)，默认为DEBUG
- `capture_locals`: 可选，是否捕获局部变量，默认为False
- `max_stack_depth`: 可选，最大堆栈深度，默认为10

#### 返回值

装饰后的函数，执行结果与原函数相同，异常发生时返回错误类型名称。

### set_error_handler(handler=None)

设置错误信息处理器。

#### 参数

- `handler`: 可选，错误信息处理函数，接收错误信息字典作为参数，可为None

### report_error(error_type, error_reason, capture_code_context=True, **kwargs)

手动报告错误。

#### 参数

- `error_type`: 错误类型
- `error_reason`: 错误原因
- `capture_code_context`: 可选，是否捕获代码上下文和局部变量，默认为True
- `**kwargs`: 可选，额外的上下文信息和配置选项

## 错误信息结构

错误处理器接收到的`error_info`字典包含以下主要字段：

```python
{
    'error': {
        'type': 'ZeroDivisionError',  # 错误类型
        'message': 'division by zero',  # 错误信息
        'timestamp': '2023-10-01 12:00:00',  # 时间戳
        'exception_chain': [],  # 异常链信息
        'level': 'DEBUG'  # 错误级别
    },
    'location': {
        'filename': 'example.py',  # 文件名
        'line_number': 10,  # 行号
        'function_name': 'divide_numbers',  # 函数名
        'source_code': 'return a / b',  # 源代码行
        'module': 'example'  # 模块名
    },
    'code_context': {
        'lines': [],  # 代码上下文行列表
        'error_line': 10  # 错误行号
    },
    'stack_trace': [],  # 堆栈跟踪信息
    'highlighted_code': {},  # 高亮代码信息
    'configuration': {
        'capture_code_context': True,  # 配置信息
        'capture_locals': False,
        'max_stack_depth': 10,
        'error_level': 'DEBUG'
    }
}
```

## 示例代码

完整的示例代码请查看`example_usage.py`文件，包含了各种使用场景的演示。

## 运行示例

```bash
# 运行基本示例
python example_usage.py

# 运行异步示例
python example_usage.py async

# 运行类方法示例
python example_usage.py class

# 运行高级配置示例
python example_usage.py advanced
```

## 注意事项

1. 装饰器会自动捕获并处理异常，默认情况下不会向上传播异常，而是返回错误类型名称
2. 使用`propagate_errors`参数可以指定需要向上传播的异常类型
3. 使用`ignore_errors`参数可以指定需要忽略的异常类型
4. 局部变量捕获功能(`capture_locals`)可能会影响性能，建议仅在调试时启用
5. 最大堆栈深度(`max_stack_depth`)可以控制堆栈跟踪信息的详细程度
6. 错误处理器内部的异常不会影响原程序的执行

## 许可证

本项目采用MIT许可证。