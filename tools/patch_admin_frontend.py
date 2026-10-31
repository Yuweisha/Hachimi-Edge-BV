"""重建流程加入 sid 同步；前端加接口列表 / 重建 / 游戏控制。"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/admin_ui.py"
s = io.open(P, encoding="utf-8").read()

# ---------- 后端：rebuild 先 rebuild 再 sync sid ----------
old = '''    if path == "/api/rebuild":
        r = _run_tool("rebuild_replay_decl.py")
        st = status()
        st["rebuild"] = r
        return 200, "application/json", json.dumps(st, ensure_ascii=False).encode()'''
new = '''    if path == "/api/rebuild":
        r1 = _run_tool("rebuild_replay_decl.py")
        r2 = _run_tool("sync_all_sid.py")
        st = status()
        st["rebuild"] = {"ok": r1["ok"] and r2["ok"], "out": r1["out"] + "\\n" + r2["out"]}
        return 200, "application/json", json.dumps(st, ensure_ascii=False).encode()'''
assert old in s, "rebuild API 未匹配"
s = s.replace(old, new, 1)

# ---------- 前端：数据卡片加按钮 ----------
old2 = '''      <div class="stat"><div class="v" id="s-size">-</div><div class="k">数据大小</div></div>
    </div>
  </div>'''
new2 = '''      <div class="stat"><div class="v" id="s-size">-</div><div class="k">数据大小</div></div>
    </div>
    <div style="display:flex;gap:8px;margin-top:12px;align-items:center">
      <button onclick="rebuild()" style="background:#1f6feb;border-color:#1f6feb">一键重建</button>
      <button id="btn-game" onclick="gameToggle()">启动游戏</button>
      <span id="game-state" style="font-size:12px;color:var(--dim)"></span>
    </div>
    <div id="rebuild-out" style="font-size:11px;color:var(--dim);margin-top:8px;white-space:pre-wrap"></div>
  </div>

  <div class="card">
    <h2>接口列表 <span id="ep-sum" style="font-weight:400;text-transform:none"></span></h2>
    <div style="max-height:260px;overflow:auto">
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr>
          <th style="text-align:left;color:var(--dim);padding:6px 8px;border-bottom:1px solid var(--line)">路径</th>
          <th style="text-align:left;color:var(--dim);padding:6px 8px;border-bottom:1px solid var(--line);width:90px">长度</th>
          <th style="text-align:left;color:var(--dim);padding:6px 8px;border-bottom:1px solid var(--line);width:60px">状态</th>
        </tr></thead>
        <tbody id="ep-body"></tbody>
      </table>
    </div>
  </div>'''
assert old2 in s, "数据卡片未匹配"
s = s.replace(old2, new2, 1)

# ---------- 前端：refresh 加 game / endpoints ----------
old3 = '''    const online = !sw.intercept;
    $('m-online').classList.toggle('on', online);
    $('m-local').classList.toggle('on', !online);
  }catch(e){ $('sub').textContent = '连接失败'; }'''
new3 = '''    const online = !sw.intercept;
    $('m-online').classList.toggle('on', online);
    $('m-local').classList.toggle('on', !online);

    // 游戏状态
    const g = $('btn-game');
    if(g){
      g.textContent = s.game ? '停止游戏' : '启动游戏';
      g.style.color = s.game ? '#ff7b72' : '';
      $('game-state').textContent = s.game ? '运行中' : '未启动';
    }

    // 接口列表
    const eps = s.endpoints || [];
    const okN = eps.filter(e => e.ok && !e.empty).length;
    const emptyN = eps.filter(e => e.empty).length;
    const badN = eps.filter(e => !e.ok && !e.empty).length;
    const summ = $('ep-sum');
    if(summ) summ.textContent = '（共 ' + eps.length + '：可用 ' + okN + ' · 空 ' + emptyN + ' · 缺失 ' + badN + '）';
    const body = $('ep-body');
    if(body){
      body.innerHTML = eps.map(e => {
        const color = e.empty ? '#d29922' : (e.ok ? '#3fb950' : '#f85149');
        const txt = e.empty ? '空响应' : (e.ok ? '可用' : '缺失');
        return '<tr><td style="padding:5px 8px;border-bottom:1px solid #1e232c;font-family:ui-monospace,monospace">'
          + e.path + '</td><td style="padding:5px 8px;border-bottom:1px solid #1e232c">'
          + (e.declared || '-') + '</td><td style="padding:5px 8px;border-bottom:1px solid #1e232c;color:'
          + color + '">' + txt + '</td></tr>';
      }).join('');
    }
  }catch(e){ $('sub').textContent = '连接失败'; }'''
assert old3 in s, "refresh 未匹配"
s = s.replace(old3, new3, 1)

# ---------- 前端：加 rebuild / gameToggle 函数 ----------
old4 = '''async function pullLog(){'''
new4 = '''async function rebuild(){
  const out = $('rebuild-out');
  if(out) out.textContent = '重建中…';
  const st = await api('/api/rebuild');
  const r = st.rebuild || {};
  if(out) out.textContent = (r.ok ? '✓ ' : '✗ ') + (r.out || '').split('\\n').slice(-6).join('\\n');
  refresh();
}

async function gameToggle(){
  const alive = $('btn-game').textContent.includes('停止');
  await api('/api/game?action=' + (alive ? 'stop' : 'start'));
  setTimeout(refresh, 900);
}

async function pullLog(){'''
assert old4 in s, "pullLog 未匹配"
s = s.replace(old4, new4, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已加：接口列表 + 重建（含 sid 同步）+ 游戏控制")
