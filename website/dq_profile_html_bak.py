# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
import re


no_zip_instructions = r'''<p><strong>Click any "Download" links to download your drawings.</strong> You can also view playback and find quest pages by clicking/tapping the drawings below.</p>

<p id="save_page_info">
To save your entire profile: 1\) Open this page on a desktop/laptop computer. 2\) <a href="#" class="load_all">Click here to pre-load all images</a>. 3\) Click "File" then "Save As...", select the "Webpage, Complete" option, then save to your computer.
</p>

<p class="power_users"><em>Power users only:</em> If you are using an image download extensin, either make sure you download linked images only, or <a href="#" class="load_all">click here to load all images at once</a> and then use your extension. <strong>It's simplest to just click "Download" on each below!</strong> Or use the instructions above to download the page.</p>'''

new_no_zip_instructions = r'<div id="no_zip_download_instructions">{}</div>'.format(no_zip_instructions)

zip_instructions = '''
<div id="zip_download_instructions">
    <h3>Download Instructions</h3>
    <p>
    The <a href="/">DrawQuest Archive</a> is only available online for a short time, so please be sure to download your drawings!
    </p>
    <ul>
    <li id="zip_download_container"><em>On a desktop computer?</em> <a href="http://drawquest-zips.s3-website-us-east-1.amazonaws.com/{username}.zip">Download a ZIP file of {username}'s drawings</a>.</li>
    <li id="zip_ios_info">
    <em>On iPhone / iPad?</em> Tap any "Download" links below to save individual drawings to your device. Or use a desktop computer to download a <a href="http://drawquest-zips.s3-website-us-east-1.amazonaws.com/{username}.zip">ZIP file</a> of them all.
    </li>
    </ul>
    <p id="gallery_info">
    More content is available—find Quest galleries by clicking Quest titles below, or visit the <a href="/">DrawQuest Archive homepage</a> for other users and the Quest of the Day pages.
    </p>
</div>
'''


style_add = '''
        #no_zip_download_instructions { display:none; }
        #zip_download_instructions { display:block; }

        #zip_download_instructions {
            font-size:.9em;
            border:1px solid #67ceda;
            border-radius:14px;
            display:inline-block;
            padding:0 14px;
        }
        #zip_download_instructions h3 {
            font-size:.8em;
            margin:8px 0 0 0;
        }
        #zip_download_instructions ul {
            padding:inherit;
            padding-left:1.5em;
        }
        #zip_download_instructions li {
            margin-bottom:1em;
        }
        #zip_download_container a {
            font-weight:bold;
        }
'''

def format_page(page, username):
    if '#no_zip_download_instructions' not in page:
        page = re.sub(r'<style>', r'<style>' + style_add, page)
    if 'id="no_zip_download_instructions"' not in page:
        new_instructions = new_no_zip_instructions + zip_instructions.format(username=username)
        page = re.sub(no_zip_instructions, new_instructions, page)
    page = re.sub(r'<div id="quests_sort_info"><em>Sorted by popularity.</em></div>', '', page)
    page = re.sub(r'http://drawquest-export.s3-website-us-east-1.amazonaws.com/', '/', page)
    return page


base_dir = sys.argv[1]


for user_dir in sorted(os.listdir(base_dir)):
    user_dir = os.path.abspath(os.path.join(base_dir, user_dir))
    username = os.path.basename(user_dir)
    if username == '000exporter':
        continue
    print username,

    if not os.path.isdir(user_dir):
        print
        continue

    index_path = os.path.join(user_dir, 'index.html')

    shutil.copy(index_path, os.path.join(os.path.dirname(index_path), 'index.html.no-zip.bak'))
    user_s3_path = 's3://drawquest-export/{}/'.format(username)
    subprocess.Popen(['aws', 's3', 'cp',
                      os.path.join(user_dir, 'index.html'),
                      user_s3_path + 'index.html.no-zip.bak'], stdout=subprocess.PIPE).communicate()
    print ' .',

    with open(index_path) as page:
        new_page_contents = format_page(page.read(), username)

    new_path = os.path.join(os.path.dirname(index_path), 'index.zip.html')
    with open(new_path, 'w') as page:
        page.write(new_page_contents)
    print '.',

    os.rename(new_path, index_path)
    print '.',

    subprocess.Popen(['aws', 's3', 'cp',
                      os.path.join(user_dir, 'index.html'),
                      user_s3_path + 'index.html'], stdout=subprocess.PIPE).communicate()

    with open('./dq_profile_update_progress', 'a') as progress:
        progress.write(username)

    print '!'

