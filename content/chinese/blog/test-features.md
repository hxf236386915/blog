---
title: "功能测试文章"
date: 2026-02-07T14:30:00+08:00
draft: false
description: "测试 Markdown 渲染、代码高亮、Mermaid 图表和 Shortcodes"
categories: ["测试"]
tags: ["Test", "Feature"]
---

## 1. 文本格式测试

**加粗文本**
*斜体文本*
~~删除线文本~~
`行内代码`

## 2. 列表测试

### 无序列表
- 项目 A
- 项目 B
  - 子项目 B1

### 有序列表
1. 第一步
2. 第二步

## 3. 代码高亮测试

```python
def hello_world():
    print("Hello, World!")
    return True
```

```javascript
const greet = (name) => {
  console.log(`Hello, ${name}!`);
}
```

## 4. Mermaid 图表测试

```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```

## 5. 引用块测试

> 这是一个引用块。
> 可以包含多行。

## 6. 表格测试

| 标题1 | 标题2 |
| --- | --- |
| 内容A | 内容B |
| 内容C | 内容D |

## 7. Shortcodes 测试

{{< notice "info" >}}
这是一个 Info 提示框 (Notice Shortcode)
{{< /notice >}}
