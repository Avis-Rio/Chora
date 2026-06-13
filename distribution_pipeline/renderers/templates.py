BASE_CARD_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #ddd;
      font-family: {body_font}, sans-serif;
    }}
    .card {{
      width: {width}px;
      height: {height}px;
      position: relative;
      overflow: hidden;
      background: {bg};
      color: {fg};
      padding: {padding}px;
      border: 1px solid rgba(0,0,0,.18);
    }}
    .brand {{
      position: absolute;
      top: {brand_offset}px;
      left: {brand_offset}px;
      font-size: 24px;
      letter-spacing: 3px;
      opacity: .62;
    }}
    .index {{
      position: absolute;
      right: {brand_offset}px;
      top: {brand_offset}px;
      font-size: 42px;
      color: {accent};
      font-family: {title_font}, serif;
    }}
    .title {{
      max-width: 78%;
      margin-top: 20%;
      font-family: {title_font}, serif;
      font-size: {title_size}px;
      line-height: 1.16;
      font-weight: 600;
    }}
    .body {{
      max-width: 74%;
      margin-top: 46px;
      font-size: {body_size}px;
      line-height: 1.55;
    }}
    .metaphor {{
      position: absolute;
      left: {padding}px;
      bottom: {padding}px;
      max-width: 58%;
      color: {accent};
      font-size: 24px;
      line-height: 1.4;
      opacity: .86;
    }}
    .rule {{
      position: absolute;
      right: {padding}px;
      bottom: {padding}px;
      width: 34%;
      height: 1px;
      background: {accent};
      opacity: .8;
    }}
  </style>
</head>
<body>
  <main class="card" data-card-type="{card_type}" data-style-id="{style_id}">
    <div class="brand">Chora · Rhizomata</div>
    <div class="index">{index}</div>
    <h1 class="title">{title}</h1>
    <div class="body">{body}</div>
    <div class="metaphor">{metaphor}</div>
    <div class="rule"></div>
  </main>
</body>
</html>
"""
