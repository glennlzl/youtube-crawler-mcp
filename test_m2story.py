#!/usr/bin/env python3
"""
测试 YouTube Crawler MCP - m2story 频道
"""

import asyncio
import json
import sys
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, '/Users/glennlzsml/Desktop/youtubeCrawlerMcp')

from src.youtube_client import YouTubeClient
from src.transcript_extractor import TranscriptExtractor
from src.summarizer import VideoSummarizer


async def test_channel_metadata():
    """测试 1: 获取频道元数据"""
    print("=" * 80)
    print("测试 1: 获取 @m2story 频道元数据")
    print("=" * 80)

    try:
        client = YouTubeClient()
        metadata = client.get_channel_metadata("@m2story")

        if metadata:
            print(f"\n✅ 频道信息获取成功!")
            print(f"\n频道名称: {metadata.title}")
            print(f"频道 ID: {metadata.channel_id}")
            print(f"订阅数: {metadata.subscriber_count:,}")
            print(f"视频总数: {metadata.video_count:,}")
            print(f"总观看: {metadata.view_count:,}")
            print(f"创建时间: {metadata.published_at.date()}")
            print(f"描述: {metadata.description[:200]}...")
            return metadata.channel_id
        else:
            print("\n❌ 未找到频道")
            return None

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_latest_videos(channel_id: str, n: int = 2):
    """测试 2: 获取最新视频列表"""
    print("\n" + "=" * 80)
    print(f"测试 2: 获取最新 {n} 个视频")
    print("=" * 80)

    try:
        client = YouTubeClient()
        videos = client.get_latest_videos(channel_id, max_results=n)

        if videos:
            print(f"\n✅ 找到 {len(videos)} 个视频!")
            for i, video in enumerate(videos, 1):
                print(f"\n视频 {i}:")
                print(f"  标题: {video.title}")
                print(f"  ID: {video.video_id}")
                print(f"  发布时间: {video.published_at}")
                print(f"  时长: {video.duration_seconds}秒 ({video.duration_seconds // 60}分{video.duration_seconds % 60}秒)")
                print(f"  观看: {video.view_count:,}")
                print(f"  有字幕: {'✅' if video.has_subtitles else '❌'}")
            return videos
        else:
            print("\n❌ 未找到视频")
            return []

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_transcript_extraction(video):
    """测试 3: 提取转录文本"""
    print("\n" + "=" * 80)
    print(f"测试 3: 提取转录 - {video.title}")
    print("=" * 80)

    try:
        extractor = TranscriptExtractor()

        print(f"\n⏳ 提取字幕/转录中...")
        print(f"   视频有字幕: {'✅' if video.has_subtitles else '❌'}")
        if video.default_audio_language:
            print(f"   检测到语言: {video.default_audio_language}")

        # Prepare metadata for language detection
        video_metadata_dict = {
            "snippet": {
                "defaultAudioLanguage": video.default_audio_language,
            }
        }

        transcript = extractor.get_transcript(video.video_id, video_metadata_dict)

        if transcript:
            print(f"\n✅ 转录提取成功!")
            print(f"   来源: {transcript.source}")
            print(f"   语言: {transcript.language}")
            print(f"   文本长度: {len(transcript.text)} 字符")
            print(f"\n   预览 (前 300 字符):")
            print(f"   {transcript.text[:300]}...")
            return transcript
        else:
            print("\n❌ 转录提取失败")
            return None

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_ai_summary(video, transcript):
    """测试 4: AI 摘要生成"""
    print("\n" + "=" * 80)
    print(f"测试 4: AI 摘要生成 (DeepSeek Reasoner)")
    print("=" * 80)

    try:
        summarizer = VideoSummarizer()

        print(f"\n⏳ 使用 DeepSeek Reasoner 生成摘要...")
        print(f"   AI Provider: {summarizer.provider}")
        print(f"   Model: {summarizer.model}")

        summary = summarizer.summarize_video(video, transcript, include_full_transcript=False)

        if summary:
            print(f"\n✅ 摘要生成成功!")
            print(f"\n" + "─" * 80)
            print(f"📹 视频: {summary.title}")
            print(f"🔗 URL: {summary.url}")
            print(f"📅 发布: {summary.published_at.date()}")
            print(f"⏱️  时长: {summary.duration_seconds // 60}分{summary.duration_seconds % 60}秒")
            print(f"👁️  观看: {summary.view_count:,}")
            print(f"─" * 80)

            print(f"\n📝 摘要:")
            print(f"{summary.summary}")

            print(f"\n🎯 关键点:")
            for i, point in enumerate(summary.key_points, 1):
                print(f"  {i}. {point}")

            if summary.highlights:
                print(f"\n⭐ 亮点:")
                for highlight in summary.highlights:
                    print(f"  • {highlight}")

            print(f"\n🏷️  话题标签:")
            print(f"  {', '.join(summary.topics)}")

            print(f"\n📊 元数据:")
            print(f"  转录来源: {summary.transcript_source}")
            print(f"  转录语言: {summary.transcript_language}")

            return summary
        else:
            print("\n❌ 摘要生成失败")
            return None

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主测试流程"""
    print("\n🎬 YouTube Crawler MCP - 测试 @m2story 频道")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start_time = datetime.now()

    # 测试 1: 获取频道元数据
    channel_id = await test_channel_metadata()
    if not channel_id:
        print("\n❌ 测试终止: 无法获取频道信息")
        return

    # 测试 2: 获取最新视频
    videos = await test_latest_videos(channel_id, n=2)
    if not videos:
        print("\n❌ 测试终止: 无法获取视频列表")
        return

    # 只测试第一个视频的完整流程
    video = videos[0]

    # 测试 3: 提取转录
    transcript = await test_transcript_extraction(video)
    if not transcript:
        print("\n⚠️  跳过摘要生成 (无转录)")
        return

    # 测试 4: AI 摘要
    summary = await test_ai_summary(video, transcript)

    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)
    print(f"⏱️  总耗时: {duration:.2f} 秒")
    print(f"📊 测试结果:")
    print(f"  • 频道元数据: ✅")
    print(f"  • 视频列表: ✅ ({len(videos)} 个)")
    print(f"  • 转录提取: {'✅' if transcript else '❌'}")
    print(f"  • AI 摘要: {'✅' if summary else '❌'}")

    if summary:
        # 估算成本
        tokens_input = len(transcript.text) / 4  # 粗略估计
        tokens_output = 1000  # 假设输出 1000 tokens
        cost = (tokens_input * 0.28 / 1_000_000) + (tokens_output * 0.42 / 1_000_000)
        print(f"\n💰 预估成本:")
        print(f"  • Input tokens: ~{int(tokens_input):,}")
        print(f"  • Output tokens: ~{int(tokens_output):,}")
        print(f"  • 总成本: ~${cost:.6f}")
        print(f"  • (vs GPT-4: ${cost * 40:.4f} - 节省 97.5%!)")

    print("\n🎉 测试成功!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
