#!/usr/bin/env python3
"""
Viral YouTube SEO Optimizer
Generates metadata designed for maximum virality and millions of views
"""

import re
from datetime import datetime
from ollama import chat

class ViralSEOOptimizer:
    """Optimize metadata for viral reach and millions of views"""
    
    # Viral power words for maximum CTR
    VIRAL_POWER_WORDS = [
        "Shocking", "Unbelievable", "Mind-Blowing", "Insane", "Crazy",
        "Secret", "Hidden", "Revealed", "Exposed", "Truth",
        "Ultimate", "Best", "Worst", "Most", "Top", "Exclusive",
        "Instant", "Immediate", "Fast", "Quick", "Now", "Urgent",
        "Free", "Giveaway", "Bonus", "Limited", "Proven", "Guaranteed",
        "Viral", "Trending", "Breaking", "Must-Watch", "Epic", "Legendary"
    ]
    
    # Emotional trigger words
    EMOTIONAL_TRIGGERS = {
        "fear": ["Don't", "Stop", "Warning", "Danger", "Mistake", "Avoid"],
        "curiosity": ["What", "How", "Why", "Secret", "Hidden", "Unknown"],
        "anger": ["Unacceptable", "Outrageous", "Disgusting", "Shocking"],
        "joy": ["Amazing", "Incredible", "Wonderful", "Best", "Perfect"],
        "surprise": ["Unexpected", "Surprising", "You Won't Believe", "OMG"],
        "awe": ["Mind-Blowing", "Breathtaking", "Stunning", "Spectacular"]
    }
    
    # Viral title formulas
    VIRAL_FORMULAS = [
        "{Number} {PowerWord} {Topic} That Will {Benefit}",
        "The {PowerWord} Truth About {Topic} Nobody Talks About",
        "{PowerWord}! What Happens When You {Action} Will {Emotion}",
        "Stop! Don't {Action} Until You Watch This {Topic} Video",
        "How I {Achievement} in {Timeframe} (My {PowerWord} Secret)",
        "You Won't Believe What {Person} Did With {Topic}",
        "The Ultimate {Topic} Guide: From {Beginner} to {Expert} in {Time}",
        "{PowerWord} {Topic} Hacks That {Benefit} Instantly",
        "Why {Number}% of People {Action} Wrong (And How to Fix It)",
        "{Topic} 2026: The {PowerWord} Trends You Can't Miss"
    ]
    
    # Trending hashtags by category
    TRENDING_HASHTAGS = {
        "general": ["#viral", "#trending", "#fyp", "#foryou", "#youtube", "#shorts"],
        "engagement": ["#subscribe", "#like", "#share", "#comment", "#follow", "#bell"],
        "time": ["#2026", "#new", "#latest", "#now", "#today", "#breaking"],
        "quality": ["#hd", "#4k", "#highquality", "#mustwatch", "#recommended"]
    }
    
    @staticmethod
    def generate_viral_titles(topic, content_analysis, num_titles=10):
        """Generate 10 viral-optimized titles"""
        prompt = f"""Create {num_titles} VIRAL YouTube titles for this video topic: "{topic}"

Content Analysis: {content_analysis}

Use these VIRAL FORMULAS:
1. Curiosity Gap: "You Won't Believe What Happens When..."
2. Numbers + Shock: "5 Things That Will Change Your Life"
3. Challenge: "Why Everything You Know About X is Wrong"
4. Time Sensitive: "Do This Before It's Too Late (2026)"
5. Personal Story: "How I Gained 10K Subscribers in 3 Days"
6. FOMO: "Stop Scrolling! This Changes Everything"
7. Question Hook: "What If I Told You...?"
8. Secret/Reveal: "The Algorithm Trick No One Talks About"
9. Transformation: "From Zero to Hero: My Journey"
10. Trend Jacking: "Reacting to [Trending Topic]"

POWER WORDS: Shocking, Unbelievable, Mind-Blowing, Secret, Ultimate, Viral, Trending, Exclusive, Proven, Instant, Breaking, Must-Watch

REQUIREMENTS:
- Each title must include at least 1 power word
- Use numbers where possible (odd numbers work best: 3, 5, 7, 9)
- Include emotional triggers (curiosity, surprise, fear of missing out)
- Keep under 70 characters for mobile optimization
- Use 1-2 relevant emojis strategically
- Make them click-worthy but authentic

Provide exactly {num_titles} titles numbered 1-10."""
        
        response = chat(
            model='kimi-k2.5:cloud',
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response.message.content
    
    @staticmethod
    def generate_viral_description(topic, titles, keywords, search_data, video_duration):
        """Generate viral-optimized description"""
        prompt = f"""Create a VIRAL YouTube description for: "{topic}"

VIRAL TITLES: {titles}

SEO KEYWORDS: {', '.join(keywords[:15])}

COMPETITOR DATA: {search_data}

VIDEO DURATION: {video_duration:.1f} seconds

STRUCTURE (Follow exactly):

HOOK (First 2 lines - MOST IMPORTANT):
- Start with power words (Shocking, Unbelievable, Must-Watch)
- Include main keyword in first 60 characters
- Create curiosity gap
- Use 2-3 strategic emojis
- Make it impossible to scroll past

BODY SECTION:
- Write 3-4 paragraphs with natural keyword integration
- Include timestamp chapters (00:00 Intro, 00:30 Main Content, etc.)
- Add social proof ("Join millions who've watched")
- Mention value proposition clearly
- Use bullet points for readability

VIRAL CTA SECTION:
- Subscribe CTA with urgency ("Subscribe NOW before this goes viral")
- Engagement bait ("Comment 'YES' if you agree")
- Share incentive ("Share with 3 friends who need to see this")
- Notification bell mention ("Turn on 🔔 so you don't miss out")
- FOMO trigger ("This video won't be up forever")

SEO KEYWORD BLOCK (15-20 keywords):
List all high-volume, trending, and long-tail keywords separated by commas

VIRAL HASHTAGS (20-25 tags):
Include mix of: #viral #trending #fyp #[Topic]Viral #2026 #MustWatch #Subscribe #ViralVideo

THUMBNAIL OPTIMIZATION:
Suggest thumbnail text, colors, and elements that would maximize CTR

POSTING STRATEGY:
Best day/time to post for maximum virality

Make this description designed to get MILLIONS of views and 1000s of subscribers daily!"""
        
        response = chat(
            model='kimi-k2.5:cloud',
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response.message.content
    
    @staticmethod
    def extract_viral_keywords(description, topic, search_results):
        """Extract and optimize viral keywords"""
        # Primary high-volume keywords
        primary = [
            f"trending {topic}",
            f"viral {topic}",
            f"{topic} 2026",
            f"best {topic}",
            f"{topic} compilation",
            f"{topic} reaction",
            f"{topic} tutorial",
            f"{topic} tips",
            f"{topic} secrets",
            f"{topic} exposed"
        ]
        
        # Long-tail keywords
        secondary = [
            f"how to {topic} viral",
            f"{topic} for beginners",
            f"{topic} explained",
            f"{topic} breakdown",
            f"{topic} analysis",
            f"{topic} review",
            f"{topic} demo",
            f"{topic} transformation",
            f"{topic} before and after",
            f"{topic} 2026 trends"
        ]
        
        # Trending keywords
        trending = [
            "2026 trends",
            "viral 2026",
            "trending now",
            "breaking news",
            "latest update",
            "new discovery",
            "just released",
            "hot topic",
            "must watch",
            "viral video"
        ]
        
        # Extract from search results
        competitor_keywords = []
        if search_results:
            for video in search_results[:3]:
                if video.get('tags'):
                    competitor_keywords.extend(video['tags'][:5])
        
        # Combine all keywords
        all_keywords = list(set(primary + secondary + trending + competitor_keywords))
        
        return all_keywords[:30]  # Return top 30
    
    @staticmethod
    def generate_viral_hashtags(topic, keywords):
        """Generate 25-30 viral hashtags with country tags for global reach"""
        base_hashtags = [
            "#viral", "#trending", "#fyp", "#foryou", "#youtube",
            "#shorts", "#viralvideo", "#trendingnow", "#2026", "#new"
        ]
        
        topic_hashtags = [
            f"#{topic.replace(' ', '')}Viral",
            f"#{topic.replace(' ', '')}Trending",
            f"#Viral{topic.replace(' ', '')}",
            f"#Trending{topic.replace(' ', '')}",
            f"#{topic.replace(' ', '')}2026"
        ]
        
        engagement_hashtags = [
            "#Subscribe", "#LikeAndShare", "#CommentBelow",
            "#NotificationSquad", "#MustWatch", "#Recommended"
        ]
        
        # Country hashtags for global reach (Rich & Developing Countries)
        country_hashtags = [
            # Rich/Developed Countries
            "#USA", "#UK", "#Japan", "#SouthKorea", "#Australia", 
            "#Canada", "#Germany", "#France", "#Italy", "#Spain",
            "#Netherlands", "#Switzerland", "#Singapore", "#UAE", "#SaudiArabia",
            # Developing Countries (High Growth/Trending)
            "#India", "#Brazil", "#Mexico", "#Indonesia", "#Turkey",
            "#Nigeria", "#Egypt", "#Vietnam", "#Thailand", "#Philippines",
            "#Malaysia", "#Argentina", "#Colombia", "#Pakistan", "#Bangladesh"
        ]
        
        # Add keyword-based hashtags
        keyword_hashtags = [f"#{kw.replace(' ', '')}" for kw in keywords[:8]]
        
        all_hashtags = base_hashtags + topic_hashtags + engagement_hashtags + country_hashtags + keyword_hashtags
        
        return list(set(all_hashtags))[:30]  # Return 30 unique hashtags
    
    @staticmethod
    def analyze_viral_patterns(search_results):
        """Analyze viral patterns from top videos"""
        if not search_results:
            return {}
        
        patterns = {
            "common_words": [],
            "avg_views": 0,
            "avg_likes": 0,
            "best_performer": None,
            "title_patterns": [],
            "tag_patterns": []
        }
        
        total_views = 0
        total_likes = 0
        all_words = []
        all_tags = []
        
        for video in search_results:
            total_views += video.get('views', 0)
            total_likes += video.get('likes', 0)
            
            # Extract words from title
            title_words = video.get('title', '').lower().split()
            all_words.extend(title_words)
            
            # Collect tags
            if video.get('tags'):
                all_tags.extend(video['tags'])
        
        if search_results:
            patterns["avg_views"] = total_views // len(search_results)
            patterns["avg_likes"] = total_likes // len(search_results)
            patterns["best_performer"] = search_results[0]
        
        # Find common words (excluding stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        word_freq = {}
        for word in all_words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        patterns["common_words"] = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Most common tags
        tag_freq = {}
        for tag in all_tags:
            tag_lower = tag.lower()
            tag_freq[tag_lower] = tag_freq.get(tag_lower, 0) + 1
        
        patterns["tag_patterns"] = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return patterns
    
    @staticmethod
    def get_optimal_posting_time():
        """Get optimal posting time for virality"""
        # Based on YouTube analytics data
        best_times = {
            "weekday": {
                "best": "2:00 PM - 4:00 PM",
                "good": "12:00 PM - 6:00 PM",
                "avoid": "12:00 AM - 6:00 AM"
            },
            "weekend": {
                "best": "9:00 AM - 11:00 AM",
                "good": "8:00 AM - 12:00 PM",
                "avoid": "Late Night Hours"
            }
        }
        
        current_day = datetime.now().strftime("%A")
        is_weekend = current_day in ["Saturday", "Sunday"]
        
        if is_weekend:
            return best_times["weekend"]
        else:
            return best_times["weekday"]
    
    @staticmethod
    def generate_engagement_strategy(topic):
        """Generate engagement strategy for viral growth"""
        return {
            "pin_comment": f"What's your favorite part about {topic}? Comment below! 👇",
            "cta_1": "Subscribe NOW and turn on notifications! 🔔",
            "cta_2": "Like this video if you found it helpful! 👍",
            "cta_3": "Share with someone who needs to see this! 📤",
            "engagement_bait": f"Comment 'YES' if you want more {topic} content!",
            "community_post": f"Poll: What's your biggest challenge with {topic}?",
            "cross_platform": [
                f"TikTok: Short clip with hook from this video",
                f"Instagram Reel: 30-60 second highlight",
                f"Twitter/X: Thread with key takeaways",
                f"Facebook: Share with engaging caption"
            ]
        }
    
    @staticmethod
    def create_thumbnail_suggestions(topic, content_analysis):
        """Create thumbnail optimization suggestions"""
        return {
            "text_suggestions": [
                f"OMG! {topic}",
                f"{topic} SECRETS",
                f"YOU NEED THIS",
                f"MIND = BLOWN",
                f"WAIT FOR IT..."
            ],
            "color_scheme": "Red/Yellow/Orange on dark background (high contrast)",
            "elements": [
                "Surprised/Shocked facial expression",
                "Arrow pointing to key element",
                "Circle highlighting important part",
                "Before/After split",
                "Large numbers (3, 5, 7, 10)",
                "Question marks or exclamation points"
            ],
            "font_style": "Bold, sans-serif, ALL CAPS for impact",
            "background": "Bright gradient or high-contrast solid color"
        }


class ViralMetricsTracker:
    """Track and optimize for viral metrics"""
    
    VIRAL_TARGETS = {
        "ctr": 10.0,  # Click-through rate %
        "retention_30s": 50.0,  # % still watching at 30 seconds
        "retention_50": 40.0,  # % still watching at 50% mark
        "engagement_rate": 5.0,  # Likes + Comments / Views %
        "subscriber_conversion": 1.0,  # Subscribers / Views %
        "share_rate": 2.0,  # Shares / Views %
    }
    
    @staticmethod
    def calculate_viral_score(metrics):
        """Calculate overall viral potential score"""
        score = 0
        
        if metrics.get('ctr', 0) >= ViralMetricsTracker.VIRAL_TARGETS['ctr']:
            score += 25
        if metrics.get('retention_30s', 0) >= ViralMetricsTracker.VIRAL_TARGETS['retention_30s']:
            score += 25
        if metrics.get('engagement_rate', 0) >= ViralMetricsTracker.VIRAL_TARGETS['engagement_rate']:
            score += 25
        if metrics.get('subscriber_conversion', 0) >= ViralMetricsTracker.VIRAL_TARGETS['subscriber_conversion']:
            score += 25
        
        return score
    
    @staticmethod
    def get_viral_checklist():
        """Get viral optimization checklist"""
        return [
            "✓ Title has power word + number + emotional trigger",
            "✓ Description hook in first 60 characters",
            "✓ 20-25 viral hashtags included",
            "✓ 30+ SEO keywords in description",
            "✓ Thumbnail has high contrast + face + text",
            "✓ Video length optimized (8-15 minutes)",
            "✓ Strong CTA in first 30 seconds",
            "✓ Subscribe CTA at 0:30, 2:00, and end",
            "✓ Pinned comment with engagement bait",
            "✓ Posted at optimal time (2-4 PM weekday)",
            "✓ Cross-promoted on other platforms",
            "✓ Community post created before upload"
        ]
