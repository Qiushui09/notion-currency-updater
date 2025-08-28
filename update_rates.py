import requests
import os
from datetime import datetime

def load_config():
    config = {}
    with open('config.txt', 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            config[key] = value
    return config

# 加载配置
config = load_config()
NOTION_TOKEN = config['NOTION_TOKEN']
DATABASE_ID = config['DATABASE_ID']

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_exchange_rates():
    """获取汇率数据"""
    try:
        print("正在获取汇率数据...")
        response = requests.get('https://api.exchangerate-api.com/v4/latest/CNY')
        print(f"API响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates', {})
            print(f"获取到汇率数据，包含 {len(rates)} 种货币")
            return rates
        else:
            print(f"API请求失败: {response.text}")
            return None
    except Exception as e:
        print(f"获取汇率失败: {e}")
        return None

def update_notion_rate(currency_pair, currency_code, rate, is_success=True):
    """更新或创建Notion数据库中的汇率记录"""
    
    print(f"处理货币对: {currency_pair}, 汇率: {rate}")
    
    # 查询是否存在该货币对
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    query_data = {
        "filter": {
            "property": "货币对",
            "title": {
                "equals": currency_pair
            }
        }
    }
    
    try:
        response = requests.post(query_url, headers=headers, json=query_data)
        
        if response.status_code != 200:
            print(f"查询失败: {response.text}")
            return False
            
        results = response.json().get('results', [])
        print(f"找到 {len(results)} 条现有记录")
        
        # 构建页面数据
        page_data = {
            "properties": {
                "货币对": {"title": [{"text": {"content": currency_pair}}]},
                "货币代码": {"select": {"name": currency_code}},
                "中间价": {"number": rate if rate else 0},
                "数据来源": {"select": {"name": "API自动"}},
                "状态": {"select": {"name": "正常" if is_success else "更新失败"}}
            }
        }
        
        if results:
            # 更新现有记录
            page_id = results[0]['id']
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(url, headers=headers, json=page_data)
        else:
            # 创建新记录
            url = "https://api.notion.com/v1/pages"
            page_data["parent"] = {"database_id": DATABASE_ID}
            response = requests.post(url, headers=headers, json=page_data)
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"API响应错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"更新异常 {currency_pair}: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("汇率自动更新系统启动")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 获取汇率数据
    rates = get_exchange_rates()
    if not rates:
        print("❌ 无法获取汇率数据，终止执行")
        return
    
    print(f"✅ 成功获取汇率数据")
    
    # 定义需要更新的货币对
    currency_mappings = {
        'USD': 'USD/CNY',
        'EUR': 'EUR/CNY', 
        'GBP': 'GBP/CNY',
        'JPY': 'JPY/CNY',
        'HKD': 'HKD/CNY',
        'CAD': 'CAD/CNY',
        'AUD': 'AUD/CNY'
    }
    
    print("\n开始更新各币种汇率...")
    print("-" * 30)
    
    success_count = 0
    total_count = len(currency_mappings)
    
    for currency_code, currency_pair in currency_mappings.items():
        print(f"\n处理 {currency_pair}:")
        
        if currency_code in rates:
            if rates[currency_code] != 0:
                try:
                    rate = round(1 / rates[currency_code], 4)
                    
                    if update_notion_rate(currency_pair, currency_code, rate, True):
                        print(f"✅ {currency_pair}: {rate}")
                        success_count += 1
                    else:
                        print(f"❌ {currency_pair}: 更新失败")
                        
                except Exception as e:
                    print(f"❌ {currency_pair}: 计算汇率失败 - {e}")
            else:
                print(f"❌ {currency_pair}: API返回汇率为0")
        else:
            print(f"❌ {currency_pair}: API未返回此货币数据")
    
    # 输出汇总结果
    print("\n" + "=" * 50)
    print("汇率更新汇总")
    print("=" * 50)
    print(f"总共处理: {total_count} 个货币对")
    print(f"成功更新: {success_count} 个")
    print(f"更新失败: {total_count - success_count} 个")
    print(f"成功率: {round(success_count/total_count*100, 1)}%")
    
    if success_count == total_count:
        print("🎉 所有汇率更新成功！")
    elif success_count > 0:
        print("⚠️  部分汇率更新成功，请检查失败项目")
    else:
        print("💥 所有汇率更新失败，请检查配置")
    
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

if __name__ == "__main__":
    main()
