#!/usr/bin/env python

import os
import re
import json
import shutil
import zipfile
import requests
import subprocess
from pathlib import Path
from os.path import exists
from getpass import getpass


project_dir = cwd = os.getcwd()
source_dir = project_dir + '/src/areca-amazon-s3'
work_dir = source_dir + '/temp'
repo_dir = work_dir + '/areca-backup-amazon-s3-plugin'
release_dir = source_dir + '/releases'
release_data_file = source_dir + '/release-info.json'


def main():
    restore_date()
    release_dict = read_release_info()
    shutil.rmtree(repo_dir, ignore_errors=True)
    shutil.rmtree(work_dir + '/.git', ignore_errors=True)
    Path(repo_dir).mkdir(parents=True, exist_ok=True)
    subprocess.run('git init ' + repo_dir, shell=True)
    subprocess.run('git branch -m master main', shell=True, cwd=repo_dir)
    git_config_user('Robert Bernhardt', 'https://sourceforge.net/u/rbernhardt/profile/') # unknown email
    keys = list(release_dict.keys())
    for index in sorted(keys):
        print(index)
        if release_dict[index]['zip-broken']:
            continue
        shutil.move(repo_dir + '/.git', work_dir)
        change_date(release_dict[index]['date'])
        uncompress(release_dict[index])
        shutil.move(work_dir + '/.git', repo_dir)
        commit_and_tagging(release_dict[index])
        restore_date()
        # upload release files
    git_config_user('bugtamer', '35902230+bugtamer@users.noreply.github.com')


def read_release_info():
    with open(release_data_file, 'r') as archivo:
        contenido = archivo.read()
        data = json.loads(contenido)
        return data


def uncompress(release):
    shutil.rmtree(repo_dir, ignore_errors=True)
    path_to_compressed_source_code = release_dir + '/' + release['src']['file']
    if not exists(path_to_compressed_source_code):
        print('missing', path_to_compressed_source_code)
        return
    print(path_to_compressed_source_code)
    subprocess.run('unzip {s} -d {d}'.format(s=path_to_compressed_source_code, d=repo_dir), shell=True)
    with zipfile.ZipFile(path_to_compressed_source_code, 'r') as zip_ref:
        zip_ref.extractall(repo_dir)
        file_list = zip_ref.namelist()
        container_folder_guard(file_list)
    return


# verify if the compressed file contains a containing folder or not (areca-)
def container_folder_guard(file_list):
    a_file = file_list[0].split('/')[0]
    if re.search(r'areca-', a_file):
        areca_folder = a_file.split('/')[0]
        shutil.move(repo_dir + '/' + areca_folder, work_dir)
        os.rename(work_dir + '/' + areca_folder, repo_dir)


def commit_and_tagging(release):
    version = release['version']
    title = 'Version ' + version
    release_message = title
    file_list = []
    file_list.append('- ' + release['bin']['file'])
    file_list.append('  - MD5:  ' + release['bin']['md5'])
    file_list.append('  - SHA1: ' + release['bin']['sha1'])
    file_list.append('- ' + release['src']['file'])
    file_list.append('  - MD5:  ' + release['src']['md5'])
    file_list.append('  - SHA1: ' + release['src']['sha1'])
    tag_body = '\n'.join(file_list)
    tag_message = title + '\n\n' + tag_body
    subprocess.run('git add .', shell=True, cwd=repo_dir)
    subprocess.run('git commit --message "{m}" --allow-empty'.format(m=release_message), shell=True, cwd=repo_dir)
    subprocess.run('git tag -a v{v} -m "{m}"'.format(v=version, m=tag_message), shell=True, cwd=repo_dir)


def change_date(date):
    subprocess.run('timedatectl set-ntp off', shell=True)
    subprocess.run('echo {p} | sudo -S date --utc --set="{d}"'.format(d=date, p=pwd), shell=True)
    subprocess.run('date --utc', shell=True)


def restore_date():
    subprocess.run('timedatectl set-ntp on', shell=True)
    subprocess.run('sleep 1', shell=True)
    subprocess.run('date --utc', shell=True)


def httpGet(url):
    restore_date()
    httpResponse = requests.get(url)
    response = {}
    response['content'] = httpResponse.content
    response['status_code'] = httpResponse.status_code
    return response


def git_config_user(name, email):
    subprocess.run('git config --local user.name "{}"'.format(name), shell=True, cwd=repo_dir)
    subprocess.run('git config --local user.email {}'.format(email), shell=True, cwd=repo_dir)


def show_dict(dict):
    for i in dict.keys():
        release = dict[i]
        show_release(release)
    print(len(dict.keys()))


def show_release(release, i=None):
    url = release['url']
    date = release['date']
    version = release['version']
    message = '{v} - {d} - {u}'.format(u=url, d=date, v=version)
    print(message)


if __name__ == '__main__':
    pwd = getpass()
    main()