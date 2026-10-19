# Source this file from Bash: source tools/activate-cambc.sh
cambc_project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="$cambc_project_dir/tools:$PATH"
hash -r
unset cambc_project_dir
