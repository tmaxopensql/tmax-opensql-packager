from datetime import datetime
from os import path, makedirs

import yaml, docker, docker.errors
import logging, traceback
import argparse

# label variables for convenience and readability
os = 'os'
database = 'database'
options = 'options'

name = 'name'
version = 'version'
major_version = 'major_version'
minor_version = 'minor_version'
patch_version = 'patch_version'

common = 'common'

# opensql component definitions
component_groups = {
    'os': { 'oraclelinux', 'rockylinux' },
    'database': { 'postgresql' },
    'pg_build_extensions': { 'pgaudit', 'credcheck', 'system_stats' }
}

os_repositories = {
    'oraclelinux': 'oraclelinux',
    'rockylinux': 'rockylinux/rockylinux',
}

# dnf repositories for opensql components
component_repositories = {
    'postgresql': 'https://download.postgresql.org/pub/repos/yum/reporpms/EL-{os_major_version}-x86_64/pgdg-redhat-repo-latest.noarch.rpm',
    'pgpool': 'https://www.pgpool.net/yum/rpms/{major_version}.{minor_version}/redhat/rhel-{os_major_version}-x86_64/pgpool-II-release-{major_version}.{minor_version}-{number}.noarch.rpm',
    'pg_hint_plan': 'https://github.com/ossc-db/pg_hint_plan/releases/download/REL{pg_major_version}_{major_version}_{minor_version}_{patch_version}/pg_hint_plan{pg_major_version}-{version}-1.pg{pg_major_version}.rhel{os_major_version}.x86_64.rpm',
    'pg_build_extensions': 'https://raw.githubusercontent.com/tmaxopensql/tmax-opensql-extensions/refs/heads/main/{name}/{version}/{name}-{version}-{os_name}{os_version}-pg{pg_major_version}.tar',
    'etcd': 'https://github.com/etcd-io/etcd/releases/download/v{version}/etcd-v{version}-linux-amd64.tar.gz'
}

# opensql component artifact names
component_artifacts = {
    'postgresql': {
        'postgresql{major_version}-{version}',
        'postgresql{major_version}-server-{version}',
        'postgresql{major_version}-contrib-{version}',
        'postgresql{major_version}-devel-{version}'
    },
    'pgpool': 'pgpool-II-pg{pg_major_version}-{version}',
    'postgis': 'postgis3{number}_{pg_major_version}-{version}', # epel needed
    'barman': 'barman-{version}',                               # epel needed
}

# init settings for redhat os
os_init_settings = {
    'oraclelinux': {
        common: {
            'dnf -y install tar epel-release python3',
            'dnf config-manager --enable ol{os_major_version}_codeready_builder'
        }
    },
    'rockylinux': {
        '8': {
            'dnf -y install tar epel-release python3',
            'dnf config-manager --set-enabled powertools'
        },
        '9': {
            'dnf -y install tar epel-release python3',
            'crb enable',
            'dnf config-manager --set-enabled crb'
        }
    }
}

# available version restrictions
support_versions = {
    'oraclelinux': {
        '8.0','8.1','8.2','8.3',
        '8.4','8.5','8.6','8.7',
        '8.8','8.9','8.10', '9'
    },
    'rockylinux': {
        '8.4','8.5','8.6','8.7','8.8','8.9','8.10',
        '9.0','9.1','9.2','9.3','9.4'
    },
    'postgresql': { '14.13', '15.8' },
    'pgpool': { '4.4.4' },
    'postgis': { '3.4.0' },
    'barman': { '3.11.1' },
    'pg_build_extension_install_utils': { '1.0.0' },
    'pg_hint_plan': {
        '14': { '1.4.3' },
        '15': { '1.5.2' }
    },
    'pgaudit': { '1.7.0' },
    'credcheck': { '2.8.0' },
    'system_stats': { '3.2' },
    'etcd': { '3.5.6' },
    'patroni': { '4.0.3' }
}

# docker container directories
work_directory = '/opensql'

# log directory
log_directory_name = 'logs'

# output tar name
package_name = 'opensql.tar'

# default input file name
default_input_file_name = 'input.yaml'

def __main__():

    input_file_name = get_input_yaml_file_name()

    if not path.isfile(input_file_name):
        print(f'[ERROR] there is no setting file("{input_file_name}")')
        return

    spec = read_yaml(input_file_name)

    # Check input parameters
    if os not in spec or spec[os][name] not in component_groups[os]:
        print(f'[ERROR] target OS must be set. Please input an OS argument. (available os: {component_groups[os]})')
        return

    if database not in spec or spec[database][name] not in component_groups[database]:
        print(f'[ERROR] target Database must be set. Please input Database argument. (available database: {component_groups[database]})')
        return

    if spec[os][version] not in support_versions[spec[os][name]]:
        print(f'[ERROR] os version {spec[os][version]} is not supported. (available versions: {support_versions[spec[os][name]]})')
        return
    
    if spec[database][version] not in support_versions[spec[database][name]]:
        print(f'[ERROR] database version {spec[database][version]} is not supported. (available versions: {support_versions[spec[database][name]]})')
        return

    db_version = spec[database][version]
    db_major_version = db_version.split('.')[0]

    # Check components vailidity
    for component in spec[options]:

        if component[name] not in support_versions: continue

        if db_major_version in support_versions[component[name]]:
            if component[version] not in support_versions[component[name]][db_major_version]:
                print(f'[ERROR] there is no supported version {component[version]} of {component[name]} for db major version {db_major_version}. (available versions: {support_versions[component[name]]})')
                return
            continue

        if component[version] not in support_versions[component[name]]:
            print(f'[ERROR] {component[name]} version {component[version]} is not supported. (available versions: {support_versions[component[name]]})')
            return

    specifications = parse_spec(spec)
    print(specifications)

    # Prepare a docker container based on the target os
    os_name = spec[os][name]
    os_version = spec[os][version]
    os_major_version = spec[os][version].split('.')[0]

    docker_client = docker.from_env()
    docker_image = get_os_docker_image(os_name, os_version, docker_client)

    if docker_image is None: return

    docker_container = None
    docker_container_log = None

    try:
        print(f'[INFO] make a docker container...')
        docker_container = docker_client.containers.run(docker_image, '/bin/bash', detach=True, tty=True)

        # save the logs of the docker container
        if not path.isdir(log_directory_name):
            makedirs(log_directory_name)

        docker_container_log = open(f'{log_directory_name}/{datetime.now()}.log', 'ab')

        print(f'[INFO] make a work directory...')

        execute_and_log_container(f'mkdir {work_directory}', docker_container, docker_container_log)

        # set repotrack
        success = get_repotrack_if_not_exists(docker_container, docker_container_log)

        if not success: return

        # os init settings
        if os_name in os_init_settings:

            success = init_os(os_name, os_major_version, docker_container, docker_container_log)

            if not success: return

        # database: postgresql
        if 'postgresql' == spec[database][name]:

            print(f'[INFO] pg download setting...')

            success = get_postgresql(os_major_version, db_version, docker_container, docker_container_log)

            if not success: return

        # optional components
        for component in spec[options]:

            if 'pgpool' == component[name]:
                success = get_pgpool(os_major_version, db_major_version, component, docker_container, docker_container_log)

            if 'postgis' == component[name]:
                success = get_postgis(db_major_version, component, docker_container, docker_container_log)

            if 'barman' == component[name]:
                success = get_barman(component, docker_container, docker_container_log)

            if 'pg_hint_plan' == component[name]:
                success = get_pg_hint_plan(os_major_version, db_major_version, component, docker_container, docker_container_log)

            if 'pg_build_extension_install_utils' == component[name]:
                success = get_pg_build_extension_install_utils(docker_container, docker_container_log)

            if component[name] in component_groups['pg_build_extensions']:
                success = get_pg_build_extension(spec, component, docker_container, docker_container_log)

            if 'etcd' == component[name]:
                success = get_etcd(component, docker_container, docker_container_log)

            if 'patroni' == component[name]:
                success = get_patroni(component, docker_container, docker_container_log)

            if not success: return
            else: continue

        # put spec info
        print(f'[INFO] all package download is completed.')
        result = execute_and_log_container(f'sh -c \'echo "{specifications}" > {work_directory}/METADATA\'', docker_container, docker_container_log)

        # get archive from container
        print('[INFO] make an package archive and get the archive from worker container...')
        stream, stat = docker_container.get_archive(work_directory)

        file = open(package_name, 'wb')
        for chunk in stream: file.write(chunk)
        file.close()

        print(f'[INFO] packaging is completed.')

    except Exception as e:
        logging.error(traceback.format_exc())

    finally:

        if docker_container_log is not None:
            docker_container_log.close()

        if docker_container is not None:

            docker_container.kill()
            docker_container.remove()

def get_input_yaml_file_name():

    parser = argparse.ArgumentParser(description="OpenSQL package setting file parser")

    parser.add_argument('--setting', type=str, default=default_input_file_name, help="OpenSQL package setting yaml file name")

    args = parser.parse_args()

    return args.setting

def read_yaml(file_path: str):

    if file_path is None: return None

    file = open(file_path, 'r')

    data = yaml.load(file, Loader=yaml.BaseLoader)

    return data

def execute_and_log_container(command, container, log, workdir=None):

    log.write(f'\n[{datetime.now()}] {command}\n'.encode())

    result = container.exec_run(command, workdir=workdir)

    log.write(result.output)

    return result

def parse_spec(spec: dict):

    if spec is None or type(spec) != dict: return None

    specifications = '[SUPPORTED OS VERSION]'
    specifications += f'\n{spec[os][name]} {spec[os][version]}'

    specifications += '\n[INSTALLABLE BINARIES]'
    specifications += f'\n{spec[database][name]} {spec[database][version]}'

    for component in spec[options]:
        specifications += f'\n{component[name]} {component[version]}'

    return specifications

def get_os_docker_image(os_name, os_version, docker_client):

    docker_image = None
    try:

        os_repository = os_repositories.get(os_name, os_name)

        docker_image = docker_client.images.get(os_repository+':'+os_version)

    except docker.errors.ImageNotFound:

        print(f'[WARN] docker image ({os_repository}:{os_version}) does not exist in this machine. docker pull will be started.')

    if docker_image is None:
        try:

            docker_image = docker_client.images.pull(os_repository, os_version)

            print(f'[INFO] docker image ({os_repository}:{os_version}) pull is completed.')

        except docker.errors.NotFound:

            print(f'[ERROR] docker image ({os_repository}:{os_version}) pull is failed. please check the os name and version.')
            return None

    return docker_image

def get_repotrack_if_not_exists(docker_container, docker_container_log):

    print(f'[INFO] check repotrack exists...')
    result = execute_and_log_container('command -v repotrack', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[INFO] repotrack is not found. install yum-utils with dnf...')
        result = execute_and_log_container('dnf install -y yum-utils', docker_container, docker_container_log)

        if result.exit_code != 0:
            print(f'[ERROR] yum-utils install failed.')
            return False

        print(f'[INFO] yum-utils install is completed.')

        result = execute_and_log_container('command -v repotrack', docker_container, docker_container_log)

        if result.exit_code != 0:
            print(f'[ERROR] yum-utils is installed, but repotrack is not found.')
            return False

    return True

def init_os(os_name, os_major_version, docker_container, docker_container_log):

    print(f'[INFO] os init setting...')

    epel_setting = os_init_settings[os_name]

    if common in epel_setting:
        commands = epel_setting[common]
    else:
        commands = epel_setting[os_major_version]

    for command in commands:
        result = execute_and_log_container(command.format(os_major_version=os_major_version), docker_container, docker_container_log)

        if result.exit_code != 0:
            print(f'[ERROR] os init setting is failed.\n{result.output.decode()}')
            return False

    return True

def make_component_directory(component_name, docker_container, docker_container_log):

    download_directory = work_directory + '/' + component_name
    result = execute_and_log_container(f'mkdir -p {download_directory}', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[ERROR] make a directory of {component_name} is failed.\n{result.output.decode()}')
        return None

    return download_directory

def download_rpms(artifact, directory, docker_container, docker_container_log):

    print(f'[INFO] {artifact} download...')

    download_directory = make_component_directory(directory, docker_container, docker_container_log)

    if download_directory is None: return False

    result = execute_and_log_container(f'repotrack --destdir {download_directory} {artifact}', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[ERROR] {artifact} download is failed.\n{result.output.decode()}')
        return False

    return True

def get_postgresql(os_major_version, pg_version, docker_container, docker_container_log):

    pg_major_version = pg_version.split('.')[0]

    repository_url = component_repositories['postgresql'].format(os_major_version=os_major_version)

    result = execute_and_log_container(f'dnf -y install {repository_url}', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[ERROR] dnf pg repository setting is failed.\n{result.output.decode()}')
        return False

    result = execute_and_log_container('dnf -qy module disable postgresql', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[ERROR] dnf disable default postgresql is failed.\n{result.output.decode()}')
        return False

    print(f'[INFO] pg download...')

    for artifact_format in component_artifacts['postgresql']:
        artifact = artifact_format.format(version=pg_version, major_version=pg_major_version)

        success = download_rpms(artifact, 'postgresql', docker_container, docker_container_log)

        if not success: return False

    return True

def get_pgpool(os_major_version, pg_major_version, component, docker_container, docker_container_log):

    print(f'[INFO] pgpool download setting...')

    component_version_tokens = component[version].split('.')

    format_arguments = {
        version: component[version],
        major_version: component_version_tokens[0],
        minor_version: component_version_tokens[1],
        'os_major_version': os_major_version,
        'pg_major_version': pg_major_version
    }

    number, limit = 1, 5
    while number < limit:
        format_arguments['number'] = number
        repository_url = component_repositories['pgpool'].format(**format_arguments)

        result = execute_and_log_container(f'dnf -y install {repository_url}', docker_container, docker_container_log)

        if result.exit_code == 0: break
        else: number += 1

    if number == limit:
        print(f'[ERROR] pgpool download setting is failed.')
        return False

    artifact = component_artifacts['pgpool'].format(**format_arguments)
    return download_rpms(artifact, 'pgpool', docker_container, docker_container_log)

def get_postgis(pg_major_version, component, docker_container, docker_container_log):

    print(f'[INFO] postgis download...')

    format_arguments = {
        version: component[version],
        'pg_major_version': pg_major_version
    }

    download_directory = make_component_directory('postgis', docker_container, docker_container_log)

    if download_directory is None: return False

    number, limit = 1, 10
    while number < limit:
        format_arguments['number'] = number
        artifact = component_artifacts['postgis'].format(**format_arguments)
        result = execute_and_log_container(f'repotrack --destdir {download_directory} {artifact}', docker_container, docker_container_log)

        if result.exit_code == 0: break
        else: number += 1

    if number == limit:
        print(f'[ERROR] postgis download is failed.')
        return False

    return True

def get_barman(component, docker_container, docker_container_log):

    artifact = component_artifacts['barman'].format(version=component[version])

    return download_rpms(artifact, 'barman', docker_container, docker_container_log)

def get_pg_hint_plan(os_major_version, pg_major_version, component, docker_container, docker_container_log):

    component_version_tokens = component[version].split('.')

    format_arguments = {
        version: component[version],
        major_version: component_version_tokens[0],
        minor_version: component_version_tokens[1],
        patch_version: component_version_tokens[2],
        'os_major_version': os_major_version,
        'pg_major_version': pg_major_version
    }

    artifact = component_repositories['pg_hint_plan'].format(**format_arguments)

    return download_rpms(artifact, 'pg_hint_plan', docker_container, docker_container_log)

def get_pg_build_extension_install_utils(docker_container, docker_container_log):

    print(f'[INFO] pg build extension install utils download...')

    success = download_rpms('make', 'extension-utils/make', docker_container, docker_container_log)

    if not success: return False

    success = download_rpms('llvm', 'extension-utils/llvm', docker_container, docker_container_log)

    if not success: return False

    return True

def curl_check_file_available(url, docker_container, docker_container_log):

    result = execute_and_log_container(f'curl -s -f -I {url}', docker_container, docker_container_log)

    if result.exit_code == 0: return True

    return False

def curl_download_file(url, path, docker_container, docker_container_log):

    result = execute_and_log_container(f'curl -L -s -o {path} {url}', docker_container, docker_container_log)

    if result.exit_code != 0:
        print(f'[ERROR] curl download is failed.\n({url})\n{result.output.decode()}')
        return False

    return True

def get_pg_build_extension(spec, component, docker_container, docker_container_log):

    print(f'[INFO] pg build extension [{component[name]}] download...')

    download_directory = make_component_directory(component[name], docker_container, docker_container_log)

    if download_directory is None: return False

    format_arguments = {
        name: component[name],
        version: component[version],
        'os_name': spec[os][name],
        'os_version': spec[os][version],
        'pg_major_version': spec[database][version].split('.')[0]
    }

    # first, we try downloading with os full version info
    url = component_repositories['pg_build_extensions'].format(**format_arguments)

    available = curl_check_file_available(url, docker_container, docker_container_log)

    # if url is not available, then retry with os major version
    if not available:
        print(f'[INFO] trying download pg build extension file with os major version')
        format_arguments['os_version'] = spec[os][version].split('.')[0]
        url = component_repositories['pg_build_extensions'].format(**format_arguments)
        available = curl_check_file_available(url, docker_container, docker_container_log)

    # if is not available with os major version, then we give up. no choice.
    if not available:
        print(f'[ERROR] there is no availabe pg build extension file {component} for {spec[os]} {spec[database]}')
        return False

    path = download_directory + '/tmp.tar'

    success = curl_download_file(url, path, docker_container, docker_container_log)

    if not success: return False

    result = execute_and_log_container('tar -xvf tmp.tar', docker_container, docker_container_log, download_directory)

    if result.exit_code != 0:
        print(f'[ERROR] tar -xvf is failed.\n{result.output.decode()}')
        return False

    result = execute_and_log_container('rm tmp.tar', docker_container, docker_container_log, download_directory)

    if result.exit_code != 0:
        print(f'[ERROR] rm tmp.tar is failed.\n{result.output.decode()}')
        return False

    return True

def get_etcd(component, docker_container, docker_container_log):

    print(f'[INFO] etcd download...')

    download_directory = make_component_directory(component[name], docker_container, docker_container_log)

    if download_directory is None: return False

    # parse download url of etcd
    url = component_repositories['etcd'].format(version=component[version])

    available = curl_check_file_available(url, docker_container, docker_container_log)

    # if is not available, then we give up. no choice.
    if not available:
        print(f'[ERROR] there is no availabe pg build extension file {component}')
        return False

    path = download_directory + '/tmp.tar'

    success = curl_download_file(url, path, docker_container, docker_container_log)

    if not success: return False

    result = execute_and_log_container('tar -xvf tmp.tar', docker_container, docker_container_log, download_directory)

    if result.exit_code != 0:
        print(f'[ERROR] tar -xvf is failed.\n{result.output.decode()}')
        return False

    result = execute_and_log_container('rm tmp.tar', docker_container, docker_container_log, download_directory)

    if result.exit_code != 0:
        print(f'[ERROR] rm tmp.tar is failed.\n{result.output.decode()}')
        return False

    return True

def get_patroni(component, docker_container, docker_container_log):

    print(f'[INFO] patroni dependencies download...')

    dependencies = { 'python3', 'python3-psycopg2', 'gcc', 'python3-devel' }

    for artifact in dependencies:

        success = download_rpms(artifact, f'{component[name]}-dependencies/{artifact}', docker_container, docker_container_log)

        if not success: return False

    print(f'[INFO] patroni download...')

    component_directory = make_component_directory(component[name], docker_container, docker_container_log)

    if component_directory is None: return False

    artifact = 'patroni[etcd]==' + component[version]
    result = execute_and_log_container(f'pip3 download {artifact}', docker_container, docker_container_log, component_directory)

    if result.exit_code != 0:
        print(f'[ERROR] patroni download is failed.')
        return False

    return True

# python3 package.py
if __name__ == '__main__':

    __main__()
