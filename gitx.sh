#!/bin/bash

# Function to check if the user is a Pramata user
is_pramata_user() {
    local email_domain=$(git config --get user.email | awk -F'@' '{print $2}')
    [[ $email_domain == "pramata.com" ]] && return 0 || return 1
}

# Function to check if the repository is a Pramata repository
is_pramata_repo() {
    local remote_url=$(git remote get-url origin)
    if [[ $remote_url == *"pramata"* ]]; then
        return 0 # Pramata repository
    else
        return 1 # Non-Pramata repository
    fi
}

# Function to extract the RAASNG number from the branch name
get_raasng_number() {
    local branch_name=$(git rev-parse --abbrev-ref HEAD)
    local pattern="RAASNG-([0-9]+)"
    if [[ $branch_name =~ $pattern ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

# Function to fix commit message for Pramata user in Pramata repository
fix_commit_message() {
    local commit_msg="$1"
    local pattern="^RAASNG-[0-9]+"
    if ! [[ $commit_msg =~ $pattern ]]; then
        local raasng_number=$(get_raasng_number)
        if [ -n "$raasng_number" ]; then
            commit_msg="RAASNG-$raasng_number-$commit_msg"
        else
            commit_msg="$commit_msg"
        fi
    fi
    echo "$commit_msg"
}

# Check if the user provided the "-f" flag after the command
if [ "$gitx_command" == "-f" ]; then
    # Execute the git command as is without any checks or modifications
    git "${@:2}"
    exit $?
fi

# Check if the user is a Pramata user
if is_pramata_user; then
    # Check if the repository is a Pramata repository
    if is_pramata_repo; then
        # Valid Pramata user in a Pramata repository: Proceeding with the git command.
        echo "Valid Pramata user in a Pramata repository: Proceeding with the git command."

        command="$1" # The first argument is the actual command

        if [ "$command" == "commit" ]; then
            echo "Processing The commit message to append branch tag"
            # Process the commit message to ensure it starts with "RAASNG-"
            commit_msg="$2" # The second argument is the commit message
            if [ -n "$commit_msg" ]; then
                fixed_msg=$(fix_commit_message "$commit_msg")
            fi
        fi
    else
        # Invalid Pramata user in a Non-Pramata repository: Cannot proceed with the git command.
        echo "Invalid Pramata user in a Non-Pramata repository: Cannot proceed with the git command."
        exit 1
    fi
else
    # Check if the repository is a Pramata repository
    if is_pramata_repo; then
        # Invalid Non-Pramata user in a Pramata repository: Cannot proceed with the git command.
        echo "Invalid Non-Pramata user in a Pramata repository: Cannot proceed with the git command."
        exit 1
    else
        # Valid Non-Pramata user in a Non-Pramata repository: Proceeding with the git command.
        echo "Valid Non-Pramata user in a Non-Pramata repository: Proceeding with the git command."

        command="$1" # The first argument is the actual command
        if [ "$command" == "commit" ]; then
            echo "Processing The commit message to append branch tag"
            # Process the commit message to ensure it starts with "RAASNG-"
            commit_msg="$2" # The second argument is the commit message
            if [ -n "$commit_msg" ]; then
                fixed_msg=$(fix_commit_message "$commit_msg")
            fi
        fi
    fi
fi

# Replace "gitx" with "git" in the command
command="${command/gitx/git}"

# Print the exact git command that will be executed
if [ -n "$fixed_msg" ]; then
    echo "Executing: git $command -m \"$fixed_msg\""
    # Execute the git command with the modified commit message and arguments
    git $command -m "$fixed_msg"
else
    echo "Executing: git $command ${@:2}"
    # Execute the git command as is
    git $command "${@:2}"
fi

# Put this file in /usr/local/bin/gitx
# In .bashrc or .zshrc put this line -  alias git='gitx'
