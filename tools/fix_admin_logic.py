import io

p = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/admin_ui.py"
s = io.open(p, encoding="utf-8").read()

# 1. 模式判定：在线 = 拦截关闭（intercept 不存在）
old1 = '''    // 模式判定：urlpatch_off 存在 = 在线
    const online = sw.urlpatch_off;
    $('m-online').classList.toggle('on', online);
    $('m-local').classList.toggle('on', !online);'''
new1 = '''    // 模式判定：在线录制 = 拦截关闭
    const online = !sw.intercept;
    $('m-online').classList.toggle('on', online);
    $('m-local').classList.toggle('on', !online);'''
assert old1 in s, "模式判定未匹配"
s = s.replace(old1, new1, 1)

# 2. setMode / toggle 后延时再刷新
old2 = '''async function setMode(m){
  await api('/api/mode?mode='+m);
  refresh();
}
async function toggle(name){
  await api('/api/toggle?name='+name);
  refresh();
}'''
new2 = '''async function setMode(m){
  await api('/api/mode?mode='+m);
  setTimeout(refresh, 300);
}
async function toggle(name){
  await api('/api/toggle?name='+name);
  setTimeout(refresh, 300);
}'''
assert old2 in s, "setMode 未匹配"
s = s.replace(old2, new2, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("已修模式判定 + 刷新时序")
