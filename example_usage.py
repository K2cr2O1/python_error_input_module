"""
错误监听插件使用示例

本文件展示了如何使用error_decorator插件中的功能
"""

import asyncio

# 导入错误监听插件的功能
from scan_error import error_decorator


# 示例1：使用装饰器捕获函数错误
@error_decorator
def divide_numbers(a: int, b: int) -> float:
    """一个可能会抛出异常的除法函数"""
    return a / b


# 示例2：使用装饰器捕获异步函数错误
@error_decorator
async def async_divide(a: int, b: int, **kwargs) -> float:
    """异步版本的除法函数
    
    Args:
        a: 被除数
        b: 除数
        **kwargs: 可包含上下文参数，如target_user_id, target_group_id, target_type等
    """
    # 模拟异步操作
    await asyncio.sleep(0.1)
    return a / b


# 示例3：使用带参数的装饰器指定错误消息发送目标
@error_decorator(target_type="group")  # 明确指定目标类型为群聊
async def async_divide_with_target(a: int, b: int, **kwargs) -> float:
    """指定错误消息发送目标的异步除法函数
    
    Args:
        a: 被除数
        b: 除数
        **kwargs: 可包含额外的上下文参数，会覆盖装饰器中的参数
    """
    # 模拟异步操作
    await asyncio.sleep(0.1)
    return a / b


# 示例4：自定义错误处理器 - 支持新的错误信息结构和完整的异常链
def custom_error_handler(error_info: dict) -> None:
    """
    自定义的错误处理器
    
    Args:
        error_info: 包含错误信息的字典，使用新的标准化结构
    """
    # 基本错误信息
    error_data = error_info['error']
    print(f"[自定义处理器] 捕获到错误: {error_data['type']}")
    print(f"错误信息: {error_data['message']}")
    print(f"错误发生时间: {error_data['timestamp']}")
    
    # 显示异常链信息（如果有）
    if 'exception_chain' in error_data and error_data['exception_chain']:
        print("\n异常链信息:")
        for i, chain_info in enumerate(error_data['exception_chain']):
            prefix = "原始异常" if chain_info.get('is_original', False) else f"链 #{i}"
            relation = f" [{chain_info.get('relation', '')}]" if i > 0 else ""
            print(f"  {prefix}{relation}: {chain_info['type']} - {chain_info['message']}")
    
    # 显示错误位置信息
    if 'location' in error_info and error_info['location']:
        location = error_info['location']
        print(f"\n错误位置: {location['module']}:{location['line_number']} in {location['function_name']}")
        if location['source_code']:
            print(f"  代码行: {location['source_code']}")
    
    # 显示被装饰函数的详细信息（如果有）
    decorated_func_info = {}
    for key, value in error_info.items():
        if key.startswith('decorated_function_'):
            original_key = key.replace('decorated_function_', '')
            decorated_func_info[original_key] = value
    
    if decorated_func_info:
        print("\n被装饰函数信息:")
        for key, value in decorated_func_info.items():
            print(f"  {key}: {value}")

    # 显示堆栈跟踪信息
    if 'stack_trace' in error_info and error_info['stack_trace']:
        print("\n堆栈跟踪 (前5帧):")
        for i, frame in enumerate(error_info['stack_trace'][:5]):  # 只显示前5帧避免输出过长
            print(f"  [{i+1}] {frame['filename']}:{frame['line_number']} in {frame['function_name']}")
            if frame['code']:
                print(f"      代码: {frame['code']}")

    # 显示错误发生位置的代码上下文
    if 'code_context' in error_info and error_info['code_context']:
        print("\n错误位置代码上下文:")
        for context in error_info['code_context']['lines']:
            marker = ">>>" if context.get('is_error_line', False) else "   "
            print(f"  {marker} {context['line_no']}: {context['code']}")

    print("-" * 50)


# 示例5：测试各种错误情况的函数
def test_error_cases():
    """测试各种错误情况"""
    print("\n=== 测试错误监听装饰器 ===\n")
    
    # 设置自定义错误处理器
    from scan_error import set_error_handler
    set_error_handler(custom_error_handler)
    
    # 测试1：同步函数除零错误
    print("测试1: 同步函数除零错误")
    result = divide_numbers(10, 0)
    print(f"结果: {result}\n")
    
    # 测试2：异步函数除零错误
    print("测试2: 异步函数除零错误")
    result = asyncio.run(async_divide(5, 0))
    print(f"结果: {result}\n")
    
    # 测试3：带目标参数的异步函数除零错误
    print("测试3: 带目标参数的异步函数除零错误")
    result = asyncio.run(async_divide_with_target(8, 0))
    print(f"结果: {result}\n")
    
    # 测试4：类型错误
    @error_decorator
    def type_error_function(a, b):
        return a + b
    
    print("测试4: 类型错误")
    result = type_error_function("hello", 123)
    print(f"结果: {result}\n")
    
    # 测试5：索引错误
    @error_decorator
    def index_error_function(lst):
        return lst[10]
    
    print("测试5: 索引错误")
    result = index_error_function([1, 2, 3])
    print(f"结果: {result}\n")
    
    # 测试6：属性错误
    @error_decorator
    def attribute_error_function(obj):
        return obj.nonexistent_attribute
    
    print("测试6: 属性错误")
    result = attribute_error_function("string object")
    print(f"结果: {result}\n")
    
    # 测试7：异常链
    @error_decorator
    def chained_exception_function():
        try:
            raise ValueError("原始错误")
        except ValueError as e:
            raise RuntimeError("包装错误") from e
    
    print("测试7: 异常链")
    result = chained_exception_function()
    print(f"结果: {result}\n")
    
    print("=== 测试完成 ===")


# 示例6：演示各种配置选项的使用
@error_decorator(error_level="ERROR", capture_locals=True, max_stack_depth=5)
def test_with_error_level(event=None):
    """演示设置错误级别和捕获局部变量"""
    x = 10
    y = 0
    z = x / y
    return z


@error_decorator(capture_code_context=False)  # 不捕获代码上下文
def test_without_code_context(event=None):
    """演示不捕获代码上下文"""
    return 100 / 0


@error_decorator(max_stack_depth=2)  # 限制堆栈深度
def deep_function_call(event=None):
    """演示限制堆栈深度的效果"""
    def inner_function():
        return 200 / 0
    return inner_function()


@error_decorator(ignore_errors=[ZeroDivisionError])  # 忽略特定错误
def test_ignore_error(event=None):
    """演示忽略特定类型的错误"""
    return 300 / 0


@error_decorator(propagate_errors=[ZeroDivisionError])  # 传播特定错误
def test_propagate_error(event=None):
    """演示传播特定类型的错误"""
    return 400 / 0


# 示例7：测试类方法和静态方法的使用
class TestClass:
    # 普通实例方法
    @error_decorator(target_user_id="test_user_008", target_type="instance_method")
    def instance_method(self, event=None):
        return 10 / 0
    
    # 类方法
    @error_decorator(target_user_id="test_user_009", target_type="class_method")
    @classmethod
    def class_method(cls, event=None):
        return 20 / 0
    
    # 静态方法
    @error_decorator(target_user_id="test_user_010", target_type="static_method")
    @staticmethod
    def static_method(event=None):
        return 30 / 0
    
    # 异步实例方法
    @error_decorator(target_user_id="test_user_011", target_type="async_instance_method")
    async def async_instance_method(self, event=None):
        await asyncio.sleep(0.1)
        return 40 / 0
    
    # 嵌套装饰器示例
    @error_decorator(target_user_id="test_user_012", target_type="nested_decorator")
    @error_decorator(custom_context={"additional_info": "nested_decorator_test"})
    def nested_decorator_method(self, event=None):
        return 50 / 0


# 示例7：异步测试函数
async def test_async_error_cases():
    """异步测试各种错误情况"""
    print("\n=== 异步测试错误监听装饰器 ===\n")
    
    # 设置自定义错误处理器
    from scan_error import set_error_handler
    set_error_handler(custom_error_handler)
    
    # 测试异步函数错误
    print("异步测试: 除零错误")
    result = await async_divide(100, 0)
    print(f"结果: {result}\n")
    
    print("异步测试: 带目标参数的除零错误")
    result = await async_divide_with_target(200, 0)
    print(f"结果: {result}\n")
    
    print("=== 异步测试完成 ===")


# 示例8：测试高级配置选项
def test_advanced_configs():
    """测试各种高级配置选项"""
    print("\n=== 测试高级配置选项 ===\n")
    
    # 设置自定义错误处理器
    from scan_error import set_error_handler
    set_error_handler(custom_error_handler)
    
    # 测试错误级别和局部变量捕获
    print("测试: 错误级别和局部变量捕获")
    try:
        result = test_with_error_level()
        print(f"结果: {result}\n")
    except Exception as e:
        print(f"传播了错误: {type(e).__name__}\n")
    
    # 测试不捕获代码上下文
    print("测试: 不捕获代码上下文")
    result = test_without_code_context()
    print(f"结果: {result}\n")
    
    # 测试限制堆栈深度
    print("测试: 限制堆栈深度")
    result = deep_function_call()
    print(f"结果: {result}\n")
    
    # 测试忽略特定错误
    print("测试: 忽略特定错误")
    result = test_ignore_error()
    print(f"结果: {result}\n")
    
    # 测试传播特定错误
    print("测试: 传播特定错误")
    try:
        result = test_propagate_error()
        print(f"结果: {result}\n")
    except Exception as e:
        print(f"传播了错误: {type(e).__name__}\n")


# 示例9：测试类方法和静态方法
def test_class_methods():
    """测试类方法和静态方法的错误处理"""
    print("\n=== 测试类方法和静态方法错误监听 ===\n")
    
    test_obj = TestClass()
    
    # 测试实例方法
    print("测试: 实例方法")
    result = test_obj.instance_method()
    print(f"结果: {result}\n")
    
    # 测试类方法
    print("测试: 类方法")
    result = TestClass.class_method()
    print(f"结果: {result}\n")
    
    # 测试静态方法
    print("测试: 静态方法")
    result = TestClass.static_method()
    print(f"结果: {result}\n")
    
    # 测试嵌套装饰器
    print("测试: 嵌套装饰器方法")
    result = test_obj.nested_decorator_method()
    print(f"结果: {result}\n")


# 示例9：异步测试类方法
async def test_async_class_methods():
    """异步测试类方法的错误处理"""
    print("\n=== 异步测试类方法错误监听 ===\n")
    
    test_obj = TestClass()
    
    # 测试异步实例方法
    print("异步测试: 异步实例方法")
    result = await test_obj.async_instance_method()
    print(f"结果: {result}\n")


# 主函数
if __name__ == "__main__":
    """主函数入口"""
    import sys
    
    print("错误监听插件测试脚本")
    print("=" * 50)
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "async":
        # 运行异步测试
        asyncio.run(asyncio.gather(
            test_async_error_cases(),
            test_async_class_methods()
        ))
    elif len(sys.argv) > 1 and sys.argv[1] == "class":
        # 运行类方法测试
        test_class_methods()
    elif len(sys.argv) > 1 and sys.argv[1] == "advanced":
        # 运行高级配置测试
        test_advanced_configs()
    else:
        # 运行所有测试
        test_error_cases()
        test_advanced_configs()
        test_class_methods()
    
    print("\n所有测试已完成，错误信息已输出到控制台。")