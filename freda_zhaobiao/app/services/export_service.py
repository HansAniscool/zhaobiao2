from flask import Response
import pandas as pd
from io import BytesIO
from datetime import datetime

class ExportService:
    def export_to_excel(self, tenders):
        data = []
        for t in tenders:
            data.append({
                'ID': t.id,
                '标题': t.title,
                '发布日期': t.publish_date.isoformat() if t.publish_date else '',
                '发布单位': t.organization or '',
                '地区': t.location or '',
                '摘要': t.summary or '',
                '来源网址': t.source_url or '',
                '来源网站': t.source_website or '',
                '类别': t.category or '',
                '状态': t.status,
                '浏览次数': t.view_count
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='招标信息')
        
        output.seek(0)
        
        filename = f"招标信息_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    
    def export_to_csv(self, tenders):
        data = []
        for t in tenders:
            data.append({
                'ID': t.id,
                '标题': t.title,
                '发布日期': t.publish_date.isoformat() if t.publish_date else '',
                '发布单位': t.organization or '',
                '地区': t.location or '',
                '摘要': t.summary or '',
                '来源网址': t.source_url or '',
                '来源网站': t.source_website or '',
                '类别': t.category or '',
                '状态': t.status,
                '浏览次数': t.view_count
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig', quoting=1)
        
        output.seek(0)
        
        filename = f"招标信息_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8-sig',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )

def export_tenders(tenders, format='excel'):
    service = ExportService()
    
    if format == 'csv':
        return service.export_to_csv(tenders)
    else:
        return service.export_to_excel(tenders)
