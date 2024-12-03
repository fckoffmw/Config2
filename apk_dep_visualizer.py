import sys
import argparse
import urllib.request
import tarfile
import io

def parse_arguments():
    parser = argparse.ArgumentParser(description='Alpine Linux Package Dependency Visualizer')
    parser.add_argument('-p', '--path', required=True, help='Path to the graph visualization program (not used in this script)')
    parser.add_argument('-n', '--name', required=True, help='Name of the package to analyze')
    parser.add_argument('-o', '--output', required=True, help='Path to the output file for the Mermaid code')
    parser.add_argument('-d', '--depth', type=int, required=True, help='Maximum depth of dependency analysis')

    return parser.parse_args()

def download_apkindex(url):
    try:
        response = urllib.request.urlopen(url)
        data = response.read()
        return data
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def parse_apkindex(data):
    packages = {}
    current_pkg = {}
    lines = data.decode('utf-8', errors='ignore').split('\n')
    for line in lines:
        if not line.strip():
            # End of current package entry
            if 'P' in current_pkg:
                pkg_name = current_pkg['P']
                packages[pkg_name] = current_pkg
            current_pkg = {}
        else:
            if line.startswith('P:'):
                current_pkg['P'] = line[2:].strip()
            elif line.startswith('D:'):
                deps = line[2:].strip()
                if deps:
                    # Dependencies are separated by spaces and may include version constraints
                    dep_list = [dep.split('>')[0].split('=')[0].split('<')[0] for dep in deps.split()]
                    current_pkg['D'] = dep_list
                else:
                    current_pkg['D'] = []
    return packages

def build_dependency_graph(packages, root_pkg, max_depth):
    graph = {}
    visited = set()

    def visit(pkg_name, depth):
        if depth > max_depth:
            return
        if pkg_name in visited:
            return
        visited.add(pkg_name)
        if pkg_name not in packages:
            graph[pkg_name] = []
            return
        deps = packages[pkg_name].get('D', [])
        graph[pkg_name] = deps
        for dep in deps:
            visit(dep, depth + 1)

    visit(root_pkg, 0)
    return graph

def generate_mermaid_code(graph):
    lines = ["graph TD"]
    for pkg, deps in graph.items():
        if deps:
            for dep in deps:
                lines.append(f"    {pkg} --> {dep}")
        else:
            lines.append(f"    {pkg}")
    return '\n'.join(lines)

def main():
    args = parse_arguments()
    # Paths to APKINDEX files (updated for Alpine Linux v3.18)
    apkindex_urls = [
        'https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86_64/APKINDEX.tar.gz',
        'https://dl-cdn.alpinelinux.org/alpine/v3.18/community/x86_64/APKINDEX.tar.gz',
    ]

    packages = {}

    for url in apkindex_urls:
        data = download_apkindex(url)
        if data:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
                try:
                    member = tar.getmember('APKINDEX')
                    apkindex_data = tar.extractfile(member).read()
                    pkg_info = parse_apkindex(apkindex_data)
                    packages.update(pkg_info)
                except KeyError:
                    print(f"APKINDEX not found in the tar archive from {url}")

    if args.name not in packages:
        print(f"Package '{args.name}' not found in the package index.")
        sys.exit(1)

    graph = build_dependency_graph(packages, args.name, args.depth)
    mermaid_code = generate_mermaid_code(graph)

    # Output the Mermaid code to the screen
    print(mermaid_code)

    # Write the Mermaid code to the output file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
    except Exception as e:
        print(f"Error writing to output file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()