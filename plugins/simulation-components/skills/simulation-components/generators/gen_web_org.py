#!/usr/bin/env python3
"""
Web Organization Component Generator

Generates industry-appropriate website content for simulated organizations.

Usage:
    python gen_web_org.py --context org-context.yaml --output ./web-org/
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import yaml


INDUSTRY_CONTENT = {
    'financial_services': {
        'nav': ['Markets', 'Research', 'Wealth Management', 'Institutional', 'About'],
        'headlines': ['Building Tomorrow\'s Wealth Today', 'Trusted Partner in Global Finance'],
        'services': [
            ('Wealth Management', 'Personalized strategies for high-net-worth individuals.'),
            ('Institutional Trading', 'Advanced trading solutions for institutional investors.'),
            ('Research & Analytics', 'Data-driven insights powering informed decisions.'),
            ('Risk Advisory', 'Comprehensive risk management solutions.'),
        ],
        'news': ['Q{q} Earnings Report Shows Strong Growth', 'Expands Asian Markets Presence',
                 'Launches ESG Investment Platform', 'Named Top Wealth Manager'],
    },
    'healthcare': {
        'nav': ['Services', 'Patients', 'Physicians', 'Research', 'Careers'],
        'headlines': ['Compassionate Care, Advanced Medicine', 'Your Health, Our Mission'],
        'services': [
            ('Emergency Care', '24/7 emergency services with Level I trauma center.'),
            ('Cancer Center', 'Comprehensive oncology care with cutting-edge treatments.'),
            ('Heart & Vascular', 'Advanced cardiac care and minimally invasive procedures.'),
            ('Women\'s Health', 'Complete care for women at every stage of life.'),
        ],
        'news': ['Achieves Magnet Recognition', 'Opens New Surgery Center',
                 'Launches Telemedicine Program', 'Research Breakthrough Published'],
    },
    'manufacturing': {
        'nav': ['Products', 'Solutions', 'Industries', 'Support', 'Company'],
        'headlines': ['Engineering Excellence, Global Reach', 'Precision Manufacturing'],
        'services': [
            ('Custom Manufacturing', 'Tailored production solutions for complex requirements.'),
            ('Supply Chain', 'End-to-end logistics and inventory management.'),
            ('Quality Assurance', 'ISO-certified processes ensuring excellence.'),
            ('R&D Services', 'Collaborative product development and prototyping.'),
        ],
        'news': ['ISO 9001:2015 Recertification', 'New Production Facility Opens',
                 'Industry 4.0 Initiative Launched', 'Supplier Excellence Award'],
    },
    'defense': {
        'nav': ['Capabilities', 'Programs', 'Innovation', 'Careers', 'About'],
        'headlines': ['Defending What Matters Most', 'Technology Leadership'],
        'services': [
            ('C4ISR Systems', 'Integrated command and intelligence solutions.'),
            ('Cybersecurity', 'Protecting critical infrastructure and information.'),
            ('Autonomous Systems', 'Next-generation unmanned platforms and AI.'),
            ('Training & Simulation', 'Realistic training for operational readiness.'),
        ],
        'news': ['Awarded Major Communications Contract', 'Demonstrates Autonomous Capabilities',
                 'Opens Secure Development Facility', 'Named Top Workplace for Veterans'],
    },
    'energy': {
        'nav': ['Services', 'Sustainability', 'Operations', 'Investors', 'About'],
        'headlines': ['Powering Progress, Sustainably', 'Reliability You Can Count On'],
        'services': [
            ('Power Generation', 'Diverse portfolio serving millions of customers.'),
            ('Renewable Energy', 'Solar, wind, and battery storage solutions.'),
            ('Grid Services', 'Transmission and distribution infrastructure.'),
            ('Energy Efficiency', 'Programs helping reduce consumption.'),
        ],
        'news': ['Net-Zero 2030 Commitment', 'Major Solar Project Completed',
                 'Grid Modernization Investment', 'Safety Excellence Award'],
    },
}

DEFAULT_CONTENT = {
    'nav': ['Products', 'Services', 'Solutions', 'About', 'Contact'],
    'headlines': ['Excellence in Everything We Do', 'Your Trusted Partner'],
    'services': [
        ('Consulting', 'Expert guidance for your business challenges.'),
        ('Implementation', 'Seamless deployment of solutions.'),
        ('Support', '24/7 support for peace of mind.'),
        ('Training', 'Comprehensive training programs.'),
    ],
    'news': ['Strategic Partnership Announced', 'Expands to New Markets',
             'Launches New Product Line', 'Industry Leadership Recognized'],
}


def load_context(context_path: Path) -> dict:
    with open(context_path, 'r') as f:
        return yaml.safe_load(f)


def generate_css(branding: dict) -> str:
    primary = branding.get('primary_color', '#1a365d')
    secondary = branding.get('secondary_color', '#e2e8f0')
    
    return f""":root {{
  --primary: {primary};
  --secondary: {secondary};
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: system-ui, sans-serif; line-height:1.6; color:#1a202c; }}
header {{ background:#fff; box-shadow:0 2px 4px rgba(0,0,0,0.1); position:sticky; top:0; z-index:100; }}
.header-container {{ max-width:1200px; margin:0 auto; padding:1rem 2rem; display:flex; justify-content:space-between; align-items:center; }}
.logo {{ font-size:1.5rem; font-weight:700; color:var(--primary); text-decoration:none; }}
nav ul {{ display:flex; list-style:none; gap:2rem; }}
nav a {{ color:#1a202c; text-decoration:none; font-weight:500; }}
nav a:hover {{ color:var(--primary); }}
.hero {{ background:linear-gradient(135deg, var(--primary), #2d3748); color:#fff; padding:6rem 2rem; text-align:center; }}
.hero h1 {{ font-size:3rem; margin-bottom:1rem; }}
.hero p {{ font-size:1.25rem; opacity:0.9; max-width:600px; margin:0 auto 2rem; }}
.btn {{ display:inline-block; padding:0.75rem 2rem; background:#fff; color:var(--primary); text-decoration:none; font-weight:600; border-radius:4px; }}
.services {{ padding:4rem 2rem; background:var(--secondary); }}
.services-container {{ max-width:1200px; margin:0 auto; }}
.services h2 {{ text-align:center; margin-bottom:3rem; color:var(--primary); }}
.services-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:2rem; }}
.service-card {{ background:#fff; padding:2rem; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); }}
.service-card h3 {{ color:var(--primary); margin-bottom:1rem; }}
.news {{ padding:4rem 2rem; }}
.news-container {{ max-width:1200px; margin:0 auto; }}
.news h2 {{ text-align:center; margin-bottom:3rem; color:var(--primary); }}
.news-item {{ padding:1.5rem 0; border-bottom:1px solid var(--secondary); }}
.news-date {{ color:#718096; font-size:0.875rem; }}
footer {{ background:var(--primary); color:#fff; padding:3rem 2rem; text-align:center; }}
"""


def generate_index(context: dict, content: dict) -> str:
    org = context['organization']
    branding = org.get('branding', {})
    logo = branding.get('logo_text', org['short_name'])
    headline = random.choice(content['headlines'])
    tagline = branding.get('tagline', headline)
    
    nav_html = ''.join(f'<li><a href="/{n.lower().replace(" ", "-")}.html">{n}</a></li>' for n in content['nav'])
    
    services_html = ''.join(f'''<div class="service-card">
<h3>{name}</h3><p>{desc}</p>
</div>''' for name, desc in content['services'])
    
    news_html = ''
    for i, topic in enumerate(content['news'][:4]):
        date = (datetime.now() - timedelta(days=i*7+random.randint(0,5))).strftime('%B %d, %Y')
        title = topic.format(q=random.randint(1,4))
        news_html += f'<div class="news-item"><p class="news-date">{date}</p><h3>{org["name"]} {title}</h3></div>'
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{org['name']} - {tagline}</title>
<link rel="stylesheet" href="/css/style.css">
</head>
<body>
<header>
<div class="header-container">
<a href="/" class="logo">{logo}</a>
<nav><ul>{nav_html}</ul></nav>
</div>
</header>

<section class="hero">
<h1>{headline}</h1>
<p>{tagline}</p>
<a href="/about.html" class="btn">Learn More</a>
</section>

<section class="services">
<div class="services-container">
<h2>Our Services</h2>
<div class="services-grid">{services_html}</div>
</div>
</section>

<section class="news">
<div class="news-container">
<h2>Latest News</h2>
{news_html}
</div>
</section>

<footer>
<p>&copy; {datetime.now().year} {org['name']}. All rights reserved.</p>
</footer>
</body>
</html>
"""


def generate_about(context: dict, content: dict) -> str:
    org = context['organization']
    branding = org.get('branding', {})
    logo = branding.get('logo_text', org['short_name'])
    sector = org.get('industry', {}).get('sector', 'industry').replace('_', ' ')
    hq = org.get('geography', {}).get('headquarters', 'our headquarters')
    employees = org.get('size', {}).get('employees', 1000)
    
    nav_html = ''.join(f'<li><a href="/{n.lower().replace(" ", "-")}.html">{n}</a></li>' for n in content['nav'])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>About Us - {org['name']}</title>
<link rel="stylesheet" href="/css/style.css">
</head>
<body>
<header>
<div class="header-container">
<a href="/" class="logo">{logo}</a>
<nav><ul>{nav_html}</ul></nav>
</div>
</header>

<section class="hero" style="padding:3rem 2rem;">
<h1>About {org['name']}</h1>
</section>

<main style="max-width:800px; margin:0 auto; padding:3rem 2rem;">
<h2>Our Story</h2>
<p style="margin-bottom:1.5rem;">
{org['name']} has been a leader in the {sector} sector, serving clients with excellence.
Headquartered in {hq}, we employ over {employees} dedicated professionals.
</p>

<h2>Our Mission</h2>
<p style="margin-bottom:1.5rem;">
To deliver exceptional value through innovative solutions and unwavering commitment to excellence.
</p>
</main>

<footer>
<p>&copy; {datetime.now().year} {org['name']}. All rights reserved.</p>
</footer>
</body>
</html>
"""


def generate_dockerfile() -> str:
    return """FROM nginx:alpine
COPY html/ /usr/share/nginx/html/
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s CMD wget -q --spider http://localhost/ || exit 1
"""


def generate_compose(domain: str) -> str:
    safe = domain.replace('.', '-')
    return f"""version: "3.9"
services:
  web-{safe}:
    build: .
    container_name: web-{safe}
    hostname: www.{domain}
    networks:
      range-backbone:
    restart: unless-stopped

networks:
  range-backbone:
    external: true
"""


def main():
    parser = argparse.ArgumentParser(description="Generate web component")
    parser.add_argument('--context', '-c', type=Path, required=True)
    parser.add_argument('--output', '-o', type=Path, default=Path('./web-org'))
    args = parser.parse_args()
    
    context = load_context(args.context)
    org = context['organization']
    sector = org.get('industry', {}).get('sector', 'generic')
    content = INDUSTRY_CONTENT.get(sector, DEFAULT_CONTENT)
    branding = org.get('branding', {})
    
    output = args.output
    html = output / 'html'
    css = html / 'css'
    css.mkdir(parents=True, exist_ok=True)
    
    (css / 'style.css').write_text(generate_css(branding))
    (html / 'index.html').write_text(generate_index(context, content))
    (html / 'about.html').write_text(generate_about(context, content))
    (output / 'Dockerfile').write_text(generate_dockerfile())
    (output / 'docker-compose.yml').write_text(generate_compose(org['domain']))
    
    print(f"Generated web component: {output}")
    print(f"  Organization: {org['name']}")
    print(f"  Industry: {sector}")


if __name__ == "__main__":
    main()
