#!/bin/bash
printf "Script used for creating and deploying distribution to PyPi\n"
printf "Build Distribution? (creates tar and wheel)\n"
select yn in "Yes" "No"; do
	case $yn in
		Yes ) sudo python setup.py sdist bdist_wheel; break;;
		No ) break;;
	esac
done
printf "Upload to PyPi? (requires twine)\n"
select yn in "Yes" "No"; do
	case $yn in
		Yes )
			if twine --version &>/dev/null; then
				:
			else
				printf "Twine not found. Use `pip` to install?\n"
				select yn in "Yes" "No"; do
				case $yn in
					Yes ) sudo pip install twine; break;;
					No ) break;;
				esac
			done
			fi
			twine upload dist/*;
			break;;
		No )
			break;;
	esac
done
