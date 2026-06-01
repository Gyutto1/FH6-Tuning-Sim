import sqlite3
conn = sqlite3.connect('C:/Users/12591/Documents/FH6/data/fh6_tuning_sim.db')

# All intent_tag labels need to be restored/fixed
fixes = {
    'intent_tag__free_drive': '自由驾驶测试',
    'intent_tag__full_lap': '整跑',
    'intent_tag__heavy_braking': '重刹',
    'intent_tag__intentional_exit_wheelspin': '故意出弯打滑',
    'intent_tag__intentional_heavy_braking': '故意重刹',
    'intent_tag__intentional_kerb': '故意压路肩',
    'intent_tag__intentional_oversteer': '故意甩尾',
    'intent_tag__intentional_understeer': '故意推头',
    'intent_tag__normal_driving': '普通行驶',
    'intent_tag__other': '其他意图',
    'intent_tag__straight_acceleration': '直线加速测试',
    'intent_tag__track_boundary_survey': '赛道测量标签',
}

for tag_id, label in fixes.items():
    conn.execute('UPDATE tags SET label_zh = ? WHERE tag_id = ?', (label, tag_id))

conn.commit()

# Verify
for tag_id, label in fixes.items():
    row = conn.execute('SELECT label_zh FROM tags WHERE tag_id = ?', (tag_id,)).fetchone()
    print(f'{tag_id}: {row[0]}')

conn.close()
