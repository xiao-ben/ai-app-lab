from __future__ import annotations

from dataclasses import dataclass, field

from .models import EpisodeInfo
from .summarizer import EpisodeSummary, summarize_episode


@dataclass
class XiaoheiShot:
    index: int
    slug: str
    theme: str
    structure_type: str
    core_idea: str
    composition: str
    elements: list[str]
    labels: list[str]
    filename: str

    def to_prompt(self) -> str:
        return f"""Generate one standalone 16:9 horizontal Chinese article illustration.

Visual DNA:
Pure white background. Minimalist black hand-drawn line art. Slightly wobbly pen lines. Lots of empty white space. Sparse red/orange/blue handwritten Chinese annotations. Clean absurd product-sketch feeling. No gradients, no shadows, no paper texture, no complex background, no commercial vector style, no PPT infographic look, no cute mascot poster, no children's illustration, no realistic UI.

Recurring IP character required:
小黑, a small solid-black absurd creature with white dot eyes, tiny thin legs, blank serious expression, slightly uneven hand-drawn body shape. 小黑 must perform the core conceptual action, not decorate the scene. Make 小黑 serious, deadpan, and slightly bizarre, not cute.

Theme:
{self.theme}

Structure type:
{self.structure_type}

Core idea:
{self.core_idea}

Composition:
{self.composition}

Suggested elements:
{' / '.join(self.elements)}

Chinese handwritten labels:
{' / '.join(self.labels)}

Color use:
Black for main line art and 小黑. Orange for main flow/path/arrows. Red only for key warnings/problems/results. Blue only for secondary notes or feedback/system state.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not make it a formal diagram, course slide, or dense explainer. Invent a fresh visual metaphor. Clear but not instructional, strange but clean."""


def build_xiaohei_shots(episode: EpisodeInfo, summary: EpisodeSummary | None = None) -> list[XiaoheiShot]:
    summary = summary or summarize_episode(episode)
    core = summary.core_question

    return [
        XiaoheiShot(
            index=1,
            slug="value-well",
            theme="播客封面：工作之外的价值感",
            structure_type="概念隐喻",
            core_idea=core,
            composition="画面中央是一口手绘的浅井，井沿挂着三枚工牌。小黑蹲在井边，认真往井里丢下一枚写着「头衔」的牌子，井底浮着问号。右侧大量留白。",
            elements=["怪井", "工牌", "问号", "小黑蹲投动作"],
            labels=["工作", "收入", "头衔", "还有呢"],
            filename="01-value-well.png",
        ),
        XiaoheiShot(
            index=2,
            slug="broken-compass",
            theme="灵魂拷问：外界评价失灵",
            structure_type="前后对比",
            core_idea="我们习惯用工作、收入、头衔回答「我是谁」，但人生转弯时外界评价会失灵",
            composition="左侧是一个指向 KPI 的歪罗盘，右侧罗盘碎成几片。小黑双手扶着中间断裂的罗盘轴，表情空白。橙色箭头从左指向右后断开。",
            elements=["碎罗盘", "KPI刻度", "断箭头", "小黑扶轴"],
            labels=["我是谁", "KPI", "转弯", "失灵"],
            filename="02-broken-compass.png",
        ),
        XiaoheiShot(
            index=3,
            slug="script-sunset",
            theme="故事·小阳：编剧倦怠与骑行意义",
            structure_type="角色状态",
            core_idea="做编剧十年后失去兴奋，在家乡初春骑行后意识到：若当下生活是十年后仍想过的生活，它就有意义",
            composition="小黑坐在一台老旧剧本打字机前打哈欠，机器吐出空白纸带。远处窗口露出落日与行道树花的简笔轮廓。",
            elements=["剧本机", "空白纸带", "落日窗", "小黑打哈欠"],
            labels=["十年编剧", "初春骑行", "十年后还想活", "有意义"],
            filename="03-script-sunset.png",
        ),
        XiaoheiShot(
            index=4,
            slug="cat-healing",
            theme="故事·313：小猫治愈与爱自己",
            structure_type="小漫画分镜",
            core_idea="认真负责的大人未必被奖赏，但小猫在新家打滚的那一刻，上班受的窝囊气都不重要了，重新学会爱自己",
            composition="两格小分镜：左格小黑抱着写着「窝囊气」的纸箱；右格小黑蹲在纸箱旁，看一只简笔小猫在垫子上打滚。",
            elements=["窝囊气纸箱", "打滚小猫", "分两格", "小黑蹲看"],
            labels=["认真大人", "小猫打滚", "不重要了", "爱自己"],
            filename="04-cat-healing.png",
        ),
        XiaoheiShot(
            index=5,
            slug="mask-truth",
            theme="故事·小猫：财务危机与坦白",
            structure_type="前后对比",
            core_idea="花30万维持形象后，发现坦白自己不行并不会让爱消逝，不必假装完美",
            composition="小黑正在掰开一个写着「完美」的面具，面具下露出很小的「不行」二字，旁边一盏暖灯亮着。",
            elements=["裂开面具", "暖灯", "小黑掰面具动作"],
            labels=["杀猪盘", "维持形象", "坦白", "爱还在"],
            filename="05-mask-truth.png",
        ),
        XiaoheiShot(
            index=6,
            slug="sun-blocked",
            theme="故事·盖饭：工作夺走阳光",
            structure_type="角色状态",
            core_idea="工作让人失去更重要的东西比如阳光；家人离开后才明白好工作的执着无足轻重，想对外婆说自己被照顾得很好",
            composition="小黑坐在堆满文件的格子工位里，窗外一轮太阳被文件塔挡住只露出一条光。桌角一张外婆照片简笔画。",
            elements=["文件塔", "被挡太阳", "格子工位", "外婆照片"],
            labels=["失去阳光", "下班后", "外婆", "我很好"],
            filename="06-sun-blocked.png",
        ),
        XiaoheiShot(
            index=7,
            slug="universe-menu",
            theme="故事·老李：第一次为自己做主",
            structure_type="地图路线",
            core_idea="从语言学转到餐饮管理，是第一次为自己人生做主；向宇宙点单，与妈妈重新认识彼此",
            composition="小黑拿着一本夸张菜单站在星空下的奇怪柜台前，菜单上从「语言学」弯箭头到「餐饮」。头顶几颗星像点单按钮。",
            elements=["星空柜台", "弯箭头菜单", "星形按钮", "小黑点餐"],
            labels=["第一次做主", "转行", "妈妈", "向宇宙点单"],
            filename="07-universe-menu.png",
        ),
        XiaoheiShot(
            index=8,
            slug="three-bricks",
            theme="小结：价值感的三根支柱",
            structure_type="方法分层",
            core_idea="价值感不必只来自头衔与KPI；陪伴、爱好与坦诚也能撑起「我是谁」",
            composition="三根手绘砖块叠成不稳但站住的台子，砖上分别写陪伴/爱好/坦诚。小黑站在台子上，头顶很轻的人形轮廓线。",
            elements=["三块砖", "人形轮廓", "小黑站立", "大量留白"],
            labels=["不只靠KPI", "陪伴", "爱好", "坦诚", "我是谁"],
            filename="08-three-bricks.png",
        ),
    ]
