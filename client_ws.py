import pdfkit

# HTML 表格内容（加了很多中文内容）
html_content = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: "SimSun", "Arial", sans-serif;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      border: 1px solid #333;
      padding: 8px;
      text-align: center;
    }
    th {
      background-color: #f0f0f0;
    }
  </style>
</head>
<body>
  <h1>客户身份信息登记表</h1>
  <table>
    <tr><th>项目</th><th>内容</th></tr>
    <tr><td>公司名称</td><td>北京科技有限公司</td></tr>
    <tr><td>注册地址</td><td>北京市朝阳区某某路88号</td></tr>
    <tr><td>法定代表人</td><td>张三</td></tr>
    <tr><td>公司类型</td><td>有限责任公司</td></tr>
    <tr><td>成立日期</td><td>2015年6月18日</td></tr>
    <tr><td>统一社会信用代码</td><td>91110000888888888X</td></tr>
    <tr><td>行业分类</td><td>软件开发与信息技术服务业</td></tr>
    <tr><td>股东信息</td><td>李四（60%）、王五（40%）</td></tr>
    <tr><td>开户银行</td><td>招商银行北京支行</td></tr>
    <tr><td>银行账号</td><td>6222 8888 1234 5678</td></tr>
    <tr><td>联系人</td><td>赵六</td></tr>
    <tr><td>联系电话</td><td>138-8888-8888</td></tr>
    <tr><td>经营范围</td><td>技术开发、技术服务、计算机系统集成、数据处理、软件销售等</td></tr>
    <tr><td>备注</td><td>此表为初次开户登记信息，需加盖公章</td></tr>
  </table>
</body>
</html>
"""

# 配置路径（如果你是 Windows，记得换为实际安装路径）
config = pdfkit.configuration(wkhtmltopdf=r'D:\Program Files\wkhtmltox\bin\wkhtmltopdf.exe')  # macOS/Linux
# config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')  # Windows

# 生成 PDF
pdfkit.from_string(html_content, 'output.pdf', configuration=config)
print("PDF 已生成：output.pdf")
