# Fish shell completion for apy
# Copy this file to ~/.config/fish/completions/

function __fish_apy_no_subcommand
    set -l cmd (commandline -opc)
    if [ (count $cmd) -eq 1 ]
        return 0
    end
    return 1
end

function __fish_apy_using_command
    set -l cmd (commandline -opc)
    if [ (count $cmd) -gt 1 ]
        if [ $argv[1] = $cmd[2] ]
            return 0
        end
    end
    return 1
end

# Main apy command
complete -f -c apy -n '__fish_apy_no_subcommand' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_no_subcommand' -l base-path -s b -d 'Set Anki base directory' -a '(__fish_complete_directories)'
complete -f -c apy -n '__fish_apy_no_subcommand' -l profile-name -s p -d 'Specify name of Anki profile to use'
complete -f -c apy -n '__fish_apy_no_subcommand' -l version -s V -d 'Show apy version'

# Subcommands
complete -f -c apy -n '__fish_apy_no_subcommand' -a add -d 'Add notes interactively from terminal'
complete -f -c apy -n '__fish_apy_no_subcommand' -a add-from-file -d 'Add new notes from Markdown file'
complete -f -c apy -n '__fish_apy_no_subcommand' -a add-single -d 'Add a single note from command line arguments'
complete -f -c apy -n '__fish_apy_no_subcommand' -a backup -d 'Backup Anki database to specified target file'
complete -f -c apy -n '__fish_apy_no_subcommand' -a check-media -d 'Check media'
complete -f -c apy -n '__fish_apy_no_subcommand' -a edit -d 'Edit notes that match query directly'
complete -f -c apy -n '__fish_apy_no_subcommand' -a export-to-file -d 'Export notes that match query to Markdown file'
complete -f -c apy -n '__fish_apy_no_subcommand' -a info -d 'Print some basic statistics'
complete -f -c apy -n '__fish_apy_no_subcommand' -a list-cards -d 'List cards that match query'
complete -f -c apy -n '__fish_apy_no_subcommand' -a list-cards-table -d 'List cards that match query in a tabular format'
complete -f -c apy -n '__fish_apy_no_subcommand' -a list-models -d 'List available models'
complete -f -c apy -n '__fish_apy_no_subcommand' -a list-notes -d 'List notes that match query'
complete -f -c apy -n '__fish_apy_no_subcommand' -a model -d 'Interact with the models'
complete -f -c apy -n '__fish_apy_no_subcommand' -a reposition -d 'Reposition cards that match query'
complete -f -c apy -n '__fish_apy_no_subcommand' -a review -d 'Review/Edit notes that match query'
complete -f -c apy -n '__fish_apy_no_subcommand' -a sync -d 'Synchronize collection with AnkiWeb'
complete -f -c apy -n '__fish_apy_no_subcommand' -a tag -d 'List all tags or add/remove tags from notes that match query'
complete -f -c apy -n '__fish_apy_no_subcommand' -a update-from-file -d 'Update existing or add new notes from Markdown file'

# add options
complete -f -c apy -n '__fish_apy_using_command add' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command add' -l tags -s t -d 'Specify default tags for new cards'
complete -f -c apy -n '__fish_apy_using_command add' -l model -s m -d 'Specify default model for new cards'
complete -f -c apy -n '__fish_apy_using_command add' -l deck -s d -d 'Specify default deck for new cards'

# add-single options
complete -f -c apy -n '__fish_apy_using_command add-single' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command add-single' -l parse-markdown -s p -d 'Parse input as Markdown'
complete -f -c apy -n '__fish_apy_using_command add-single' -l preset -s s -d 'Specify a preset'
complete -f -c apy -n '__fish_apy_using_command add-single' -l tags -s t -d 'Specify default tags for new cards'
complete -f -c apy -n '__fish_apy_using_command add-single' -l model -s m -d 'Specify default model for new cards'
complete -f -c apy -n '__fish_apy_using_command add-single' -l deck -s d -d 'Specify default deck for new cards'

# add-from-file and update-from-file options
for cmd in add-from-file update-from-file
    complete -f -c apy -n "__fish_apy_using_command $cmd" -l help -s h -d 'Show help'
    complete -f -c apy -n "__fish_apy_using_command $cmd" -l tags -s t -d 'Specify default tags for cards'
    complete -f -c apy -n "__fish_apy_using_command $cmd" -l deck -s d -d 'Specify default deck for cards'
    # File argument
    complete -f -c apy -n "__fish_apy_using_command $cmd" -k -a "(__fish_complete_suffix .md)"
end

complete -f -c apy -n '__fish_apy_using_command update-from-file' -l link-duplicates -s l -d 'Link duplicates to existing notes'

# export-to-file options
complete -f -c apy -n '__fish_apy_using_command export-to-file' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command export-to-file' -k -a "(__fish_complete_suffix .md)"

# list-cards options
complete -f -c apy -n '__fish_apy_using_command list-cards' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command list-cards' -l verbose -s v -d 'Print details for each card'

# list-cards-table options
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-answer -s a -d 'Display answer'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-model -s m -d 'Display model'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-cid -s c -d 'Display card ids'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-due -s d -d 'Display card due time in days'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-type -s t -d 'Display card type'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-ease -s e -d 'Display card ease'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-lapses -s l -d 'Display card number of lapses'
complete -f -c apy -n '__fish_apy_using_command list-cards-table' -l show-deck -s D -d 'Display deck'

# list-notes options
complete -f -c apy -n '__fish_apy_using_command list-notes' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command list-notes' -l show-cards -s c -d 'Print card specs'
complete -f -c apy -n '__fish_apy_using_command list-notes' -l show-raw-fields -s r -d 'Print raw field data'
complete -f -c apy -n '__fish_apy_using_command list-notes' -l verbose -s v -d 'Print note details'

# tag options
complete -f -c apy -n '__fish_apy_using_command tag' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command tag' -l add-tags -s a -d 'Add specified tags to matched notes'
complete -f -c apy -n '__fish_apy_using_command tag' -l remove-tags -s r -d 'Remove specified tags from matched notes'
complete -f -c apy -n '__fish_apy_using_command tag' -l sort-by-count -s c -d 'When listing tags, sort by note count'
complete -f -c apy -n '__fish_apy_using_command tag' -l simple -s s -d 'Only list available tags'
complete -f -c apy -n '__fish_apy_using_command tag' -l purge -s p -d 'Remove all unused tags'

# review options
complete -f -c apy -n '__fish_apy_using_command review' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command review' -l check-markdown-consistency -s m -d 'Only review notes with inconsistent Markdown'

# edit options
complete -f -c apy -n '__fish_apy_using_command edit' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command edit' -l force-multiple -s f -d 'Allow editing multiple notes'

# backup options
complete -f -c apy -n '__fish_apy_using_command backup' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command backup' -l include-media -s m -d 'Include media files in backup'
complete -f -c apy -n '__fish_apy_using_command backup' -l legacy -s l -d 'Support older Anki versions'

# model subcommands
complete -f -c apy -n '__fish_apy_using_command model' -a edit-css -d 'Edit the CSS template for the specified model'
complete -f -c apy -n '__fish_apy_using_command model' -a rename -d 'Rename model from old_name to new_name'

# model edit-css options
complete -f -c apy -n '__fish_apy_using_command model; and __fish_seen_subcommand_from edit-css' -l help -s h -d 'Show help'
complete -f -c apy -n '__fish_apy_using_command model; and __fish_seen_subcommand_from edit-css' -l model-name -s m -d 'Specify for which model to edit CSS template'
complete -f -c apy -n '__fish_apy_using_command model; and __fish_seen_subcommand_from edit-css' -l sync-after -s s -d 'Perform sync after any change'