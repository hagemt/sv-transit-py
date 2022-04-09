# v1, for ~/.zshrc or w/e
REPO_TRANSIT="$HOME/Code/transit"

# pipe the output through grep:
alias bart=' make -C "$REPO_TRANSIT" bart '
alias calt=' make -C "$REPO_TRANSIT" calt '

# and/or roll your own simple / complex versions:
alias ct=' calt ARGS="rtt mine" '
alias sf=' sf-trains '

# change to taste:
function sf-trains {
	if [[ "${1:-}" == 'home' ]]
	then
		bart | grep CIVC | grep MLBR | grep South
		calt ARGS="rtt sf"
	else
		bart | grep SBRN | grep North
		calt ARGS="rtt home"
	fi
}
