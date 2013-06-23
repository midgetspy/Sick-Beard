# Contributing to SickBeard

1. [Getting Involved](#getting-involved)
2. [How To Report Bugs](#how-to-report-bugs)
3. [Tips For Submitting Code](#tips-for-submitting-code)



## Getting Involved

There are a number of ways to get involved with the development of SickBeard. Even if you've never contributed code to an Open Source project before, we're always looking for help identifying bugs, cleaning up code, writing documentation and testing.

The goal of this guide is to provide the best way to contribute to the official SickBeard repository. Please read through the full guide detailing [How to Report Bugs](#how-to-report-bugs).

## Discussion

### Forum and IRC

The SickBeard development team frequently tracks posts on the [SickBeard Forum](http://www.sickbeard.com/forums/). If you have longer posts or questions please feel free to post them there. If you think you've found a bug please [file it in the bug tracker](#how-to-report-bugs).

Additionally most of the SickBeard development team can be found in the [#sickbeard](http://webchat.freenode.net/?channels=sickbeard) IRC channel on irc.freenode.net.


## How to Report Bugs

### Make sure it is a SickBeard bug

Many bugs reported are actually issues with the user mis-understanding of how something works (there are a bit of moving parts to an ideal setup) and most of the time can be fixed by just changing some settings to fit the users needs.

If you are new to SickBeard, it is usually a much better idea to ask for help first in the [Using SickBeard Forum](http://www.sickbeard.com/forums/) or the [SickBeard IRC channel](http://webchat.freenode.net/?channels=sickbeard). You will get much quicker support, and you will help avoid tying up the SickBeard team with invalid bug reports.

[SickBeard Issue Tracker](http://code.google.com/p/sickbeard/issues/list)


### Try the latest version of SickBeard

Bugs in old versions of SickBeard may have already been fixed. In order to avoid reporting known issues, make sure you are always testing against the latest build/source. Also, we put new code in the `development` branch first before pushing down to the `master` branch (which is what the binary builds are built off of).


## Tips For Submitting Code


### Code

**NEVER write your patches to the master branch** - it gets messy (I say this from experience!)

**ALWAYS USE A "TOPIC" BRANCH!** Personally I like the `branch-feature_name` format that way its easy to identify the branch and feature at a glance. Also please make note of any forum post / google code issue number in the pull commit so we know what you are solving (it helps with cleaning up the related items later).


Please follow these guidelines before reporting a bug:

1. **Update to the latest version** &mdash; Check if you can reproduce the issue with the latest version from the `development` branch.

2. **Use the SickBeard Forums search** &mdash; check if the issue has already been reported. If it has been, please comment on the existing issue.

3. **Provide a means to reproduce the problem** &mdash; Please provide as much details as possible, e.g. SickBeard log files (obfuscate apikey/passwords), browser and operating system versions, how you started SickBeard, and of course the steps to reproduce the problem.


### Feature requests

Please follow the bug guidelines above for feature requests, i.e. update to the latest version and search for existing issues before posting a new request.

### Pull requests

[Pull requests](https://help.github.com/articles/using-pull-requests) are welcome and the preferred way of accepting code contributions.

Please follow these guidelines before sending a pull request:

1. Update your fork to the latest upstream version.

2. Use the `development` branch to base your code off of.

3. Follow the coding conventions of the original repository. Do not change line endings of the existing file, as this will rewrite the file and loses history.

4. Keep your commits as autonomous as possible, i.e. create a new commit for every single bug fix or feature added.

5. Always add meaningful commit messages. We should not have to guess at what your code is suppose to do.
