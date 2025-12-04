import traceback
import sys
import inspect
import asyncio
from functools import wraps
from datetime import datetime
from typing import Callable, Type, Any, Optional, Dict, Union, Tuple, List


class ScanError:
    """错误监听工具类，用于捕获和处理函数执行过程中的异常"""
    
    # 错误信息处理器回调函数
    _error_handler: Optional[Callable[[Dict[str, Any]], Union[None, Any]]] = None
    
    @classmethod
    def set_error_handler(cls, handler: Optional[Callable[[Dict[str, Any]], Union[None, Any]]] = None) -> None:
        """设置错误信息处理器
        
        Args:
            handler: 错误信息处理函数，接收错误信息字典作为参数，可为None
        """
        cls._error_handler = handler
    
    @classmethod
    def error_decorator(cls, func: Optional[Callable] = None, **decorator_kwargs) -> Callable:
        """错误监听装饰器，用于全局修饰函数，自动捕获并处理执行过程中的异常
        
        - 支持同步和异步函数装饰
        - 提供无参数和带参数两种使用方式
        - 灵活的目标配置，可指定错误信息发送目标
        - 错误发生时返回错误类型名称而非抛出异常，避免程序中断
        
        参数说明:
        ----------
        func : Optional[Callable]
            需要被装饰的函数，无参数使用方式时自动传入
        **decorator_kwargs : dict
            装饰器参数，用于配置错误处理行为和目标信息
            支持的参数包括:
            - ignore_errors : List[Type[Exception]], 要忽略的异常类型列表
            - propagate_errors : List[Type[Exception]], 需要向上传播的异常类型列表
            - custom_context : dict, 自定义上下文信息，将被添加到错误信息中
            - capture_code_context : bool, 是否捕获代码上下文，默认为True
            - error_level : str, 错误信息级别 (ERROR, WARNING, INFO, DEBUG)，默认为DEBUG
            - capture_locals : bool, 是否捕获局部变量，默认为False
            - max_stack_depth : int, 最大堆栈深度，默认为10
        
        返回值:
        -------
        Callable
            装饰后的函数，执行结果与原函数相同，异常发生时返回错误类型名称
        
        使用示例:
        ---------
        # 基本用法 - 无参数装饰器
        @error_decorator
        def example_function(a, b):
            return a / b
        
        # 带参数装饰器 - 指定发送目标
        @error_decorator(target_type="group", target_group_id="123456789")
        async def async_example(a, b):
            await asyncio.sleep(0.1)
            return a / b
        
        # 高级用法 - 忽略特定异常，传播重要异常
        @error_decorator(
            ignore_errors=[ValueError],
            propagate_errors=[TypeError],
            custom_context={"module": "user_service"}
        )
        def complex_function(data):
            if not isinstance(data, dict):
                raise TypeError("数据必须是字典类型")
            if "id" not in data:
                raise ValueError("缺少必要字段'id'")
            return process_data(data)
        """
        # 支持不带参数和带参数两种装饰器使用方式
        def decorator(fn):
            # 记录原始函数信息用于调试
            original_func_info = {
                "name": fn.__name__,
                "module": fn.__module__,
                "filename": fn.__code__.co_filename if hasattr(fn, "__code__") and fn.__code__ is not None else "unknown",
                "lineno": fn.__code__.co_firstlineno if hasattr(fn, "__code__") and fn.__code__ is not None else 0
            }
            
            # 提取配置参数并添加类型注解
            ignore_errors: List[Type[Exception]] = decorator_kwargs.get("ignore_errors", [])
            propagate_errors: List[Type[Exception]] = decorator_kwargs.get("propagate_errors", [])
            custom_context: Dict[str, Any] = decorator_kwargs.get("custom_context", {})
            capture_code_context: bool = decorator_kwargs.get("capture_code_context", True)
            # 新增配置选项
            error_level: str = decorator_kwargs.get("error_level", "DEBUG")  # ERROR, WARNING, INFO, DEBUG
            capture_locals: bool = decorator_kwargs.get("capture_locals", False)  # 是否捕获局部变量
            max_stack_depth: int = decorator_kwargs.get("max_stack_depth", 10)  # 最大堆栈深度
            
            # 移除不应该传递给上下文提取的配置参数
            context_decorator_kwargs = decorator_kwargs.copy()
            for config_key in ["ignore_errors", "propagate_errors", "custom_context", "capture_code_context"]:
                context_decorator_kwargs.pop(config_key, None)
            
            # 提取并处理异常的通用函数
            def _handle_exception(e: Exception, args: Tuple, kwargs: Dict) -> str:
                # 检查是否需要忽略该异常
                for error_type in ignore_errors:
                    if isinstance(e, error_type):
                        return type(e).__name__
                
                # 检查是否需要传播该异常
                for error_type in propagate_errors:
                    if isinstance(e, error_type):
                        raise
                
                try:
                    # 合并装饰器参数和函数调用参数中的上下文信息
                    context_kwargs = kwargs.copy()
                    context_kwargs.update(context_decorator_kwargs)
                    
                    # 显式从kwargs中提取event对象，确保即使在函数过滤参数时也能保留
                    if 'event' not in context_kwargs:
                        # 尝试从调用栈中查找event对象
                        import inspect
                        frame = inspect.currentframe()
                        if frame and frame.f_back and frame.f_back.f_back:
                            frame = frame.f_back.f_back
                        else:
                            frame = None
                        if frame and 'event' in frame.f_locals:
                            context_kwargs['event'] = frame.f_locals['event']
                            print(f"从调用栈中恢复event对象: {type(context_kwargs['event']).__name__}")
                    
                    # 提取上下文信息
                    context_info = cls._extract_context_info(args, context_kwargs)
                    
                    # 添加自定义上下文信息
                    if custom_context and isinstance(custom_context, dict):
                        context_info.update(custom_context)
                    
                    # 添加被装饰函数信息
                    if isinstance(original_func_info, dict):
                        for key, value in original_func_info.items():
                            context_info[f"decorated_function_{key}"] = str(value) if value is not None else "unknown"
                    
                    # 获取错误信息并添加上下文，传递所有配置参数
                    error_info = cls._collect_error_info(
                        e, 
                        capture_code_context=capture_code_context,
                        error_level=error_level,
                        capture_locals=capture_locals,
                        max_stack_depth=max_stack_depth
                    )
                    error_info.update(context_info)
                    
                    # 调用错误处理器
                    cls._call_error_handler(error_info)
                except Exception as handler_error:
                    # 确保错误处理逻辑自身的错误不会影响原程序
                    print(f"错误装饰器内部处理失败: {handler_error}")
                
                # 返回错误类型名称
                return type(e).__name__
            
            # 处理类方法和静态方法的情况
            def make_wrapper(is_coroutine):
                @wraps(fn)
                def wrapper(*args, **kwargs):
                    try:
                        # 智能过滤上下文参数 - 只保留函数能接受的参数
                        filtered_kwargs = cls._filter_arguments(fn, kwargs)
                        
                        # 调用原始函数
                        return fn(*args, **filtered_kwargs)
                    except Exception as e:
                        # 传递完整的原始参数，确保事件对象等上下文信息被保留
                        return _handle_exception(e, args, kwargs)
                
                @wraps(fn)
                async def async_wrapper(*args, **kwargs):
                    try:
                        # 智能过滤上下文参数 - 只保留函数能接受的参数
                        filtered_kwargs = cls._filter_arguments(fn, kwargs)
                        
                        # 调用异步函数
                        return await fn(*args, **filtered_kwargs)
                    except Exception as e:
                        # 传递完整的原始参数，确保事件对象等上下文信息被保留
                        return _handle_exception(e, args, kwargs)
                
                return async_wrapper if is_coroutine else wrapper
            
            # 检查函数类型，确保正确处理各种函数类型
            is_coroutine = inspect.iscoroutinefunction(fn)
            result = make_wrapper(is_coroutine)
            
            # 处理类方法和静态方法的descriptor协议
            if isinstance(fn, (classmethod, staticmethod)):
                # 获取原始函数
                original_fn = fn.__func__ if hasattr(fn, "__func__") else fn
                
                # 如果是类方法，创建新的类方法
                if isinstance(fn, classmethod):
                    result = classmethod(make_wrapper(inspect.iscoroutinefunction(original_fn)))
                # 如果是静态方法，创建新的静态方法
                elif isinstance(fn, staticmethod):
                    result = staticmethod(make_wrapper(inspect.iscoroutinefunction(original_fn)))
            
            # 保留原始函数的特殊属性，确保装饰器嵌套时能正确工作
            for attr in ['__annotations__', '__doc__']:
                if hasattr(fn, attr):
                    try:
                        setattr(result, attr, getattr(fn, attr))
                    except (AttributeError, TypeError):
                        # 处理属性不可写的情况，特别是类方法和静态方法
                        pass
            
            # 特殊处理 __isabstractmethod__，因为类方法和静态方法可能不允许直接设置
            if hasattr(fn, '__isabstractmethod__') and getattr(fn, '__isabstractmethod__'):
                # 如果原始函数是抽象方法，确保装饰后的函数也标记为抽象方法
                if hasattr(result, '__isabstractmethod__'):
                    try:
                        setattr(result, '__isabstractmethod__', True)
                    except (AttributeError, TypeError):
                        # 处理类方法/静态方法的特殊情况
                        pass
            
            # 记录装饰器配置，用于调试和嵌套装饰器场景
            result.__scan_error_decorator_info__ = {
                'ignore_errors': ignore_errors,
                'propagate_errors': propagate_errors,
                'custom_context': custom_context,
                'capture_code_context': capture_code_context,
                'error_level': error_level,
                'capture_locals': capture_locals,
                'max_stack_depth': max_stack_depth,
                'original_func_info': original_func_info
            }
            
            return result
        
        # 处理装饰器调用方式
        return decorator(func) if func is not None else decorator
    
    @classmethod
    def _filter_arguments(cls, func: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """智能过滤函数参数，只保留函数能接受的参数
        
        此方法会分析函数签名，只保留函数定义中存在的参数，
        避免将上下文相关的参数传递给不接受这些参数的函数
        
        Args:
            func: 要调用的函数
            kwargs: 所有可用的关键字参数
            
        Returns:
            过滤后的关键字参数字典
        """
        try:
            # 获取函数签名
            sig = inspect.signature(func)
            
            # 定义标准的上下文参数列表 - 这些参数仅用于错误报告上下文
            context_keys = {
                'target_type', 'target_user_id', 'target_group_id', 'event',
                'error_context', 'custom_context', 'ignore_errors', 'propagate_errors'
            }
            
            # 过滤参数：只保留函数签名中存在的参数，排除上下文参数
            filtered_kwargs = {}
            for key, value in kwargs.items():
                # 如果参数名在函数签名中，或者不是标准上下文参数，则保留
                if key in sig.parameters or key not in context_keys:
                    filtered_kwargs[key] = value
            
            return filtered_kwargs
        except (ValueError, TypeError):
            # 如果无法获取函数签名，则只过滤已知的上下文参数
            context_keys = {
                'target_type', 'target_user_id', 'target_group_id', 'event',
                'error_context', 'custom_context', 'ignore_errors', 'propagate_errors'
            }
            return {k: v for k, v in kwargs.items() if k not in context_keys}

    @classmethod
    def report_error(cls, error_type: Type[Exception], error_reason: str, capture_code_context: bool = True, **kwargs) -> None:
        """
        手动报告错误
        
        Args:
            error_type: 错误类型
            error_reason: 错误原因
            capture_code_context: 是否捕获代码上下文和局部变量，默认为True
            **kwargs: 额外的上下文信息，可包含配置选项
        """
        # 提取配置参数
        error_level = kwargs.pop("error_level", "DEBUG")
        capture_locals = kwargs.pop("capture_locals", False)
        max_stack_depth = kwargs.pop("max_stack_depth", 10)
        
        # 创建错误实例
        error = error_type(error_reason)
        
        # 提取上下文信息
        context_info = cls._extract_context_info((), kwargs)
        
        # 获取错误信息并添加上下文
        error_info = cls._collect_error_info(error, 
                                           capture_code_context=capture_code_context,
                                           error_level=error_level,
                                           capture_locals=capture_locals,
                                           max_stack_depth=max_stack_depth)
        error_info.update(context_info)
        
        # 调用错误处理器
        cls._call_error_handler(error_info)
    
    @classmethod
    def _call_error_handler(cls, error_info: Dict[str, Any]) -> None:
        """调用错误处理器的统一方法
        
        Args:
            error_info: 包含错误信息的字典
        """
        if cls._error_handler:
            try:
                # 检查处理器是否是异步函数
                if inspect.iscoroutinefunction(cls._error_handler):
                    asyncio.create_task(cls._error_handler(error_info))
                else:
                    cls._error_handler(error_info)
            except Exception as handler_error:
                print(f"错误处理器执行失败: {handler_error}")
    
    @classmethod
    def _collect_error_info(cls, error: Exception, capture_code_context: bool = True, 
                          error_level: str = "DEBUG", capture_locals: bool = False, 
                          max_stack_depth: int = 10) -> Dict[str, Any]:
        """
        收集并组织错误信息
        
        Args:
            error: 捕获的异常对象
            capture_code_context: 是否捕获代码上下文
            error_level: 错误信息级别 (ERROR, WARNING, INFO, DEBUG)
            capture_locals: 是否捕获局部变量
            max_stack_depth: 最大堆栈深度
            
        Returns:
            包含完整错误信息的字典，结构标准化以便于处理
        """
        # 获取调用栈信息
        exc_info = sys.exc_info()
        tb = traceback.extract_tb(exc_info[2]) if exc_info[2] is not None else []
        
        # 查找错误发生的代码段
        code_context = []
        if capture_code_context and tb:
            # 获取最后一个帧（错误发生的位置）
            filename, lineno, func_name, code = tb[-1]
            
            # 尝试读取错误发生位置附近的代码
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 获取错误行附近的代码（前后各10行，提供更丰富的上下文）
                    start_line = max(0, lineno - 11)
                    end_line = min(len(lines), lineno + 10)
                    for i in range(start_line, end_line):
                        code_context.append({
                            'line_no': i + 1,
                            'code': lines[i].rstrip(),
                            'is_error_line': (i + 1) == lineno
                        })
            except (IOError, OSError):
                # 如果无法读取文件，至少保存错误行信息
                code_context.append({
                    'line_no': lineno,
                    'code': code or '',
                    'is_error_line': True
                })
        
        # 构建详细的调用栈列表
        stack_trace = []
        frame = exc_info[2]
        frame_index = 0
        
        while frame is not None and frame_index < max_stack_depth:  # 使用配置的最大堆栈深度
            try:
                # 获取帧信息
                frame_info = {
                    'filename': frame.f_code.co_filename,
                    'line_number': frame.f_lineno,
                    'function_name': frame.f_code.co_name,
                    'code': traceback.extract_stack(frame, limit=1)[0].line if traceback.extract_stack(frame, limit=1) else '',
                    'module': frame.f_code.co_filename.split('\\')[-1] if '\\' in frame.f_code.co_filename else frame.f_code.co_filename
                }
                
                # 尝试获取局部变量信息（排除敏感信息）
                if capture_code_context and capture_locals:
                    local_vars = {}
                    for var_name, var_value in frame.f_locals.items():
                        # 跳过可能包含敏感信息的变量
                        if var_name.startswith('_') or var_name in ['password', 'token', 'secret', 'key', 'api_key', 'auth_token', 'credentials']:
                            local_vars[var_name] = '<filtered>'
                        else:
                            try:
                                # 限制值的字符串表示长度
                                str_value = str(var_value)
                                if len(str_value) > 150:
                                    str_value = str_value[:150] + '...'
                                local_vars[var_name] = str_value
                            except Exception:
                                local_vars[var_name] = '<unable to represent>'
                    
                    if local_vars:
                        frame_info['local_variables'] = local_vars
                
                # 尝试获取当前帧的源代码上下文
                if capture_code_context:
                    try:
                        with open(frame.f_code.co_filename, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            start_line = max(0, frame.f_lineno - 6)
                            end_line = min(len(lines), frame.f_lineno + 5)
                            context_lines = []
                            for i in range(start_line, end_line):
                                context_lines.append({
                                    'line_no': i + 1,
                                    'code': lines[i].rstrip(),
                                    'is_current_line': (i + 1) == frame.f_lineno
                                })
                            frame_info['source_context'] = context_lines
                    except (IOError, OSError, UnicodeDecodeError):
                        pass
                
                stack_trace.append(frame_info)
                frame = frame.f_back
                frame_index += 1
            except Exception:
                break
        
        # 完善异常链信息处理
        exception_chain = []
        current_error = error
        chain_index = 0
        
        # 最多收集10层异常链
        while current_error is not None and chain_index < 10:
            chain_info = {
                'type': type(current_error).__name__,
                'message': str(current_error),
                'index': chain_index
            }
            
            # 添加原始异常标记
            if chain_index == 0:
                chain_info['is_original'] = True
            
            # 尝试获取异常的traceback
            try:
                if hasattr(current_error, '__traceback__') and current_error.__traceback__:
                    chain_info['traceback'] = traceback.format_exception(
                        type(current_error), current_error, current_error.__traceback__
                    )
            except Exception:
                pass
            
            exception_chain.append(chain_info)
            
            # 移动到下一个异常（__cause__ 优先于 __context__）
            if current_error.__cause__ is not None:
                current_error = current_error.__cause__
                chain_info['relation'] = 'caused_by'
            elif current_error.__context__ is not None and not current_error.__suppress_context__:
                current_error = current_error.__context__
                chain_info['relation'] = 'context_for'
            else:
                break
            
            chain_index += 1
        
        # 获取完整的错误回溯信息
        full_traceback = traceback.format_exception(type(error), error, error.__traceback__)
        
        # 构建标准化的错误信息结构
        error_info = {
            # 基本错误信息
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': cls._get_timestamp(),
                'exception_chain': exception_chain,
                'level': error_level  # 添加错误级别
            },
            
            # 错误发生位置
            'location': {
                'filename': tb[-1][0] if tb else 'unknown',
                'line_number': tb[-1][1] if tb else 0,
                'function_name': tb[-1][2] if tb else 'unknown',
                'source_code': tb[-1][3] if tb else '',
                'module': tb[-1][0].split('\\')[-1] if tb and '\\' in tb[-1][0] else tb[-1][0] if tb else 'unknown'
            } if tb else None,
            
            # 代码上下文（仅当启用时）
            'code_context': {
                'lines': code_context,
                'error_line': tb[-1][1] if tb else 0
            } if capture_code_context and tb else None,
            
            # 调用栈信息
            'stack_trace': stack_trace,
            
            # 原始回溯信息
            'raw_traceback': full_traceback,
            
            # 高亮代码（仅当启用时）
            'highlighted_code': cls._generate_highlighted_code(code_context, tb[-1][1] if tb else 0) if capture_code_context and tb else None,
            
            # 配置信息
            'configuration': {
                'capture_code_context': capture_code_context,
                'capture_locals': capture_locals,
                'max_stack_depth': max_stack_depth,
                'error_level': error_level
            }
        }
        
        return error_info
    
    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳
        
        Returns:
            格式化的时间字符串
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @classmethod
    def _extract_context_info(cls, args: Tuple, kwargs: Dict) -> Dict[str, Any]:
        """从函数参数中提取上下文信息
        
        Args:
            args: 函数的位置参数元组
            kwargs: 函数的关键字参数字典
            
        Returns:
            包含上下文信息的字典
        """
        context_info = {}
        
        # 提取位置参数信息
        for i, arg in enumerate(args):
            try:
                # 限制值的字符串表示长度
                str_value = str(arg)
                if len(str_value) > 50:
                    str_value = str_value[:50] + '...'
                context_info[f'arg_{i}'] = str_value
            except Exception:
                context_info[f'arg_{i}'] = '<unable to represent>'
        
        # 提取关键字参数信息
        for key, value in kwargs.items():
            # 跳过可能包含敏感信息的键
            if key.startswith('_') or key in ['password', 'token', 'secret', 'key', 'api_key', 'auth_token']:
                context_info[key] = '<filtered>'
            else:
                try:
                    # 限制值的字符串表示长度
                    str_value = str(value)
                    if len(str_value) > 100:
                        str_value = str_value[:100] + '...'
                    context_info[key] = str_value
                except Exception:
                    context_info[key] = '<unable to represent>'
        
        # 添加调用栈信息
        try:
            import inspect
            current_frame = inspect.currentframe()
            if current_frame and current_frame.f_back:
                caller_frame = current_frame.f_back
                context_info['caller_function'] = caller_frame.f_code.co_name
                context_info['caller_filename'] = caller_frame.f_code.co_filename
                context_info['caller_line_number'] = caller_frame.f_lineno
        except Exception:
            pass
        
        return context_info
    
    @classmethod
    def _generate_highlighted_code(cls, code_context: List[Dict], error_line: int) -> Dict:
        """生成高亮显示的代码片段，用于错误位置可视化
        
        Args:
            code_context: 代码上下文列表
            error_line: 错误行号
            
        Returns:
            包含高亮代码信息的字典
        """
        if not code_context:
            return None
        
        highlighted = {
            'lines': [],
            'error_line': error_line,
            'error_line_index': -1
        }
        
        for i, line_info in enumerate(code_context):
            line_no = line_info['line_no']
            code = line_info['code']
            is_error_line = line_info.get('is_error_line', False)
            
            # 确定行类型
            if is_error_line:
                line_type = 'error'
                highlighted['error_line_index'] = i
            elif line_no < error_line:
                line_type = 'before'
            else:
                line_type = 'after'
            
            highlighted['lines'].append({
                'line_no': line_no,
                'code': code,
                'type': line_type,
                'indent_level': len(code) - len(code.lstrip())
            })
        
        return highlighted
    
# 创建全局实例
scan_error = ScanError()

# 导出常用方法
set_error_handler = scan_error.set_error_handler
error_decorator = scan_error.error_decorator
report_error = scan_error.report_error