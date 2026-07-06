# MonoRepo

**Source PDF:** `MonoRepo.pdf`  
**Path:** `papers/MonoRepo.pdf`  

---

--- Page 1 ---
contributed articles
DOI:10.1145/2854146
This article outlines the scale of that
Google’s monolithic repository provides codebase and details Google’s custom-
built monolithic source repository and
a common source of truth for tens of
the reasons the model was chosen.
thousands of developers around the world.
Google uses a homegrown version-con-
trol system to host one large codebase
BY RACHEL POTVIN AND JOSH LEVENBERG visible to, and used by, most of the soft-
ware developers in the company. This
Why Google centralized system is the foundation of
many of Google’s developer workflows.
Here, we provide background on the
systems and workflows that make fea-
Stores Billions sible managing and working produc-
tively with such a large repository. We
explain Google’s “trunk-based devel-
opment” strategy and the support sys-
of Lines tems that structure workflow and keep
Google’s codebase healthy, including
software for static analysis, code clean-
up, and streamlined code review.
of Code
Google-Scale
Google’s monolithic software reposi-
tory, which is used by 95% of its soft-
ware developers worldwide, meets
in a Single
the definition of an ultra-large-scale4
system, providing evidence the sin-
gle-source repository model can be
scaled successfully.
Repository
The Google codebase includes ap-
proximately one billion files and has
a history of approximately 35 million
commits spanning Google’s entire 18-
year existence. The repository contains
86TBa of data, including approximately
a Total size of uncompressed content, excluding
release branches.
EARLY GOOGLE EMPLOYEES decided to work with a key insights
shared codebase managed through a centralized
˽ Google has shown the monolithic model
source control system. This approach has served of source code management can scale
to a repository of one billion files, 35
Google well for more than 16 years, and today the vast million commits, and tens of thousands of
developers.
majority of Google’s software assets continues to be
˽ Benefits include unified versioning,
stored in a single, shared repository. Meanwhile, the extensive code sharing, simplified
dependency management, atomic
number of Google software developers has steadily changes, large-scale refactoring,
collaboration across teams, flexible code
increased, and the size of the Google codebase
ownership, and code visibility.
has grown exponentially (see Figure 1). As a result, ˽ Drawbacks include having to create
and scale tools for development and
the technology used to host the codebase has also execution and maintain code health, as
well as potential for codebase complexity
evolved significantly.
(such as unnecessary dependencies).
78 COMMUNICATIONS OF THE ACM | JULY 2016 | VOL. 59 | NO. 7

--- Page 2 ---
JULY 2016 | VOL. 59 | NO. 7 | COMMUNICATIONS OF THE ACM 79
SETAICOSSA
SYROB
JIRDNA/ZCIWEIKASU
ANOWI
YB
EGAMI
two billion lines of code in nine million than 25,000 Google software develop- both the interactive use case, or hu-
unique source files. The total number ers from dozens of offices in countries man users, and automated use cases.
of files also includes source files cop- around the world. On a typical work- Larger dips in both graphs occur dur-
ied into release branches, files that are day, they commit 16,000 changes to the ing holidays affecting a significant
deleted at the latest revision, configu- codebase, and another 24,000 changes number of employees (such as Christ-
ration files, documentation, and sup- are committed by automated systems. mas Day and New Year’s Day, Ameri-
porting data files; see the table here for Each day the repository serves billions can Thanksgiving Day, and American
a summary of Google’s repository sta- of file read requests, with approximate- Independence Day).
tistics from January 2015. ly 800,000 queries per second during In October 2012, Google’s central
In 2014, approximately 15 million peak traffic and an average of approxi- repository added support for Windows
lines of code were changedb in approxi- mately 500,000 queries per second and Mac users (until then it was Linux-
mately 250,000 files in the Google re- each workday. Most of this traffic origi- only), and the existing Windows and
pository on a weekly basis. The Linux nates from Google’s distributed build- Mac repository was merged with the
kernel is a prominent example of a and-test systems.c main repository. Google’s tooling for
large open source software repository Figure 2 reports the number of repository merges attributes all histori-
containing approximately 15 million unique human committers per week cal changes being merged to their orig-
lines of code in 40,000 files.14 to the main repository, January 2010– inal authors, hence the corresponding
Google’s codebase is shared by more July 2015. Figure 3 reports commits bump in the graph in Figure 2. The ef-
per week to Google’s main repository fect of this merge is also apparent in
b Includes only reviewed and committed code over the same time period. The line Figure 1.
and excludes commits performed by auto- for total commits includes data for The commits-per-week graph shows
mated systems, as well as commits to release
the commit rate was dominated by
branches, data files, generated files, open
human users until 2012, at which
source files imported into the repository, and c Google open sourced a subset of its internal
other non-source-code files. build system; see http://www.bazel.io point Google switched to a custom-

--- Page 3 ---
contributed articles
Figure 1. Millions of changes committed to Google’s central repository over time. Google repository statistics, January 2015.
Total number of files 1 billion
Number of source files 9 million
40 M
Lines of source code 2 billion
Depth of history 35 million commits
Size of content 86TB
30 M
Commits per workday 40,000
20 M source-control implementation for
hosting the central repository, as
discussed later. Following this tran-
10 M sition, automated commits to the re-
pository began to increase. Growth in
the commit rate continues primarily
due to automation.
Jan. 2000 Jan. 2005 Jan. 2010 Jan. 2015 Managing this scale of repository
and activity on it has been an ongoing
challenge for Google. Despite several
years of experimentation, Google
Figure 2. Human committers per week. was not able to find a commercial-
ly available or open source version-
control system to support such scale
Unique human users per week
in a single repository. The Google
proprietary system that was built to
15,000
store, version, and vend this codebase
is code-named Piper.
10,000 Background
Before reviewing the advantages
and disadvantages of working with
a monolithic repository, some back-
5,000
ground on Google’s tooling and work-
flows is needed.
Piper and CitC. Piper stores a single
Jan. 2010 Jan. 2011 Jan. 2012 Jan. 2013 Jan. 2014 Jan. 2015 large repository and is implement-
ed on top of standard Google infra-
structure, originally Bigtable,2 now
Spanner.3 Piper is distributed over
Figure 3. Commits per week. 10 Google data centers around the
world, relying on the Paxos6 algorithm
to guarantee consistency across rep-
Human commits Total commits licas. This architecture provides a
300,000 high level of redundancy and helps
optimize latency for Google soft-
ware developers, no matter where
225,000
they work. In addition, caching and
asynchronous operations hide much
of the network latency from develop-
150,000
ers. This is important because gain-
ing the full benefit of Google’s cloud-
75,000 based toolchain requires developers
to be online.
Google relied on one primary Perforce
instance, hosted on a single machine,
Jan. 2010 Jan. 2011 Jan. 2012 Jan. 2013 Jan. 2014 Jan. 2015 coupled with custom caching infrastruc-
ture1 for more than 10 years prior to the
launch of Piper. Continued scaling of
80 COMMUNICATIONS OF THE ACM | JULY 2016 | VOL. 59 | NO. 7

--- Page 4 ---
contributed articles
the Google repository was the main All writes to files are stored as snap- Several workflows take advantage of
motivation for developing Piper. shots in CitC, making it possible to re- the availability of uncommitted code
Since Google’s source code is one of cover previous stages of work as need- in CitC to make software developers
the company’s most important assets, ed. Snapshots may be explicitly named, working with the large codebase more
security features are a key consider- restored, or tagged for review. productive. For instance, when send-
ation in Piper’s design. Piper supports CitC workspaces are available on ing a change out for code review, devel-
file-level access control lists. Most of any machine that can connect to the opers can enable an auto-commit op-
the repository is visible to all Piper cloud-based storage system, making tion, which is particularly useful when
users;d however, important configura- it easy to switch machines and pick code authors and reviewers are in dif-
tion files or files including business- up work without interruption. It also ferent time zones. When the review is
critical algorithms can be more tightly makes it possible for developers to marked as complete, the tests will run;
controlled. In addition, read and write view each other’s work in CitC work- if they pass, the code will be commit-
access to files in Piper is logged. If sen- spaces. Storing all in-progress work in ted to the repository without further
sitive data is accidentally committed the cloud is an important element of human intervention. The Google code-
to Piper, the file in question can be the Google workflow process. Work- browsing tool CodeSearch supports
purged. The read logs allow admin- ing state is thus available to other simple edits using CitC workspaces.
istrators to determine if anyone ac- tools, including the cloud-based build While browsing the repository, devel-
cessed the problematic file before it system, the automated test infrastruc- opers can click on a button to enter
was removed. ture, and the code browsing, editing, edit mode and make a simple change
In the Piper workflow (see Figure 4), and review tools. (such as fixing a typo or improving
developers create a local copy of files in
the repository before changing them. Figure 4. Piper workflow.
These files are stored in a workspace
owned by the developer. A Piper work-
space is comparable to a working copy Sync user Code
workspace Write code Commit
in Apache Subversion, a local clone to repo review
in Git, or a client in Perforce. Updates
from the Piper repository can be pulled
into a workspace and merged with on-
going work, as desired (see Figure 5).
Figure 5. Piper team logo “Piper is Piper expanded recursively;” design source: Kirrily
A snapshot of the workspace can be
Anderson.
shared with other developers for re-
view. Files in a workspace are commit-
ted to the central repository only after
going through the Google code-review
process, as described later.
Most developers access Piper
through a system called Clients in
the Cloud, or CitC, which consists of
a cloud-based storage backend and a
Linux-only FUSE13 file system. Devel-
opers see their workspaces as directo-
ries in the file system, including their
changes overlaid on top of the full
Piper repository. CitC supports code
browsing and normal Unix tools with
no need to clone or sync state locally.
Developers can browse and edit files
anywhere across the Piper reposito-
ry, and only modified files are stored
in their workspace. This structure
means CitC workspaces typically con-
sume only a small amount of storage
(an average workspace has fewer than
10 files) while presenting a seamless
view of the entire Piper codebase to
the developer.
d Over 99% of files stored in Piper are visible to
all full-time Google engineers.
JULY 2016 | VOL. 59 | NO. 7 | COMMUNICATIONS OF THE ACM 81

--- Page 5 ---
contributed articles
a comment). Then, without leaving When new features are developed,
the code browser, they can send their both new and old code paths com-
changes out to the appropriate review- monly exist simultaneously, controlled
ers with auto-commit enabled. through the use of conditional flags.
Piper can also be used without CitC. Piper and CitC This technique avoids the need for
Developers can instead store Piper a development branch and makes
make working
workspaces on their local machines. it easy to turn on and off features
Piper also has limited interoperability productively through configuration updates rather
with Git. Over 80% of Piper users today than full binary releases. While some
use CitC, with adoption continuing to with a single, additional complexity is incurred for
grow due to the many benefits provid- developers, the merge problems of
monolithic source
ed by CitC. a development branch are avoided.
Piper and CitC make working pro- repository possible Flag flips make it much easier and
ductively with a single, monolithic faster to switch users off new imple-
at the scale of the
source repository possible at the scale mentations that have problems. This
of the Google codebase. The design Google codebase. method is typically used in project-
and architecture of these systems were specific code, not common library
both heavily influenced by the trunk- code, and eventually flags are retired
based development paradigm em- so old code can be deleted. Google
ployed at Google, as described here. uses a similar approach for rout-
Trunk-based development. Google ing live traffic through different code
practices trunk-based development on paths to perform experiments that can
top of the Piper source repository. The be tuned in real time through configu-
vast majority of Piper users work at the ration changes. Such A/B experiments
“head,” or most recent, version of a can measure everything from the per-
single copy of the code called “trunk” formance characteristics of the code
or “mainline.” Changes are made to to user engagement related to subtle
the repository in a single, serial order- product changes.
ing. The combination of trunk-based Google workflow. Several best prac-
development with a central repository tices and supporting systems are re-
defines the monolithic codebase mod- quired to avoid constant breakage in
el. Immediately after any commit, the the trunk-based development model,
new code is visible to, and usable by, where thousands of engineers commit
all other developers. The fact that Piper thousands of changes to the repository
users work on a single consistent view on a daily basis. For instance, Google
of the Google codebase is key for pro- has an automated testing infrastruc-
viding the advantages described later ture that initiates a rebuild of all af-
in this article. fected dependencies on almost every
Trunk-based development is benefi- change committed to the repository.
cial in part because it avoids the pain- If a change creates widespread build
ful merges that often occur when it is breakage, a system is in place to auto-
time to reconcile long-lived branches. matically undo the change. To reduce
Development on branches is unusual the incidence of bad code being com-
and not well supported at Google, mitted in the first place, the highly
though branches are typically used customizable Google “presubmit” in-
for releases. Release branches are cut frastructure provides automated test-
from a specific revision of the reposi- ing and analysis of changes before
tory. Bug fixes and enhancements that they are added to the codebase. A set of
must be added to a release are typically global presubmit analyses are run for
developed on mainline, then cherry- all changes, and code owners can cre-
picked into the release branch (see ate custom analyses that run only on
Figure 6). Due to the need to maintain directories within the codebase they
stability and limit churn on the release specify. A small set of very low-level
branch, a release is typically a snap- core libraries uses a mechanism simi-
shot of head, with an optional small lar to a development branch to enforce
number of cherry-picks pulled in from additional testing before new versions
head as needed. Use of long-lived are exposed to client code.
branches with parallel development An important aspect of Google cul-
on the branch and mainline is exceed- ture that encourages code quality is the
ingly rare. expectation that all code is reviewed
82 COMMUNICATIONS OF THE ACM | JULY 2016 | VOL. 59 | NO. 7

--- Page 6 ---
contributed articles
before being committed to the reposi- them into two phases. With this ap- performing large-scale code changes
tory. Most developers can view and proach, a large backward-compatible at Google. Using Rosie is balanced
propose changes to files anywhere change is made first. Once it is com- against the cost incurred by teams
across the entire codebase—with the plete, a second smaller change can needing to review the ongoing stream
exception of a small set of highly con- be made to remove the original pat- of simple changes Rosie generates.
fidential code that is more carefully tern that is no longer referenced. A As Rosie’s popularity and usage grew,
controlled. The risk associated with Google tool called Rosief supports the it became clear some control had to
developers changing code they are first phase of such large-scale clean- be established to limit Rosie’s use
not deeply familiar with is mitigated ups and code changes. With Rosie, to high-value changes that would be
through the code-review process and developers create a large patch, ei- distributed to many reviewers, rather
the concept of code ownership. The ther through a find-and-replace op- than to single atomic changes or re-
Google codebase is laid out in a tree eration across the entire repository jected. In 2013, Google adopted a for-
structure. Each and every directory or through more complex refactor- mal large-scale change-review proc-
has a set of owners who control wheth- ing tools. Rosie then takes care of ess that led to a decrease in the number
er a change to files in their directory splitting the large patch into smaller of commits through Rosie from 2013
will be accepted. Owners are typically patches, testing them independently, to 2014. In evaluating a Rosie change,
the developers who work on the proj- sending them out for code review, the review committee balances the
ects in the directories in question. A and committing them automati- benefit of the change against the costs
change often receives a detailed code cally once they pass tests and a code of reviewer time and repository churn.
review from one developer, evaluating review. Rosie splits patches along We later examine this and similar
the quality of the change, and a com- project directory lines, relying on the trade-offs more closely.
mit approval from an owner, evaluating code-ownership hierarchy described In sum, Google has developed a
the appropriateness of the change to earlier to send patches to the appro- number of practices and tools to sup-
their area of the codebase. priate reviewers. port its enormous monolithic code-
Code reviewers comment on as- Figure 7 reports the number of base, including trunk-based devel-
pects of code quality, including de- changes committed through Rosie opment, the distributed source-code
sign, functionality, complexity, testing, on a monthly basis, demonstrating repository Piper, the workspace cli-
naming, comment quality, and code the importance of Rosie as a tool for ent CitC, and workflow-support-tools
style, as documented by the various Critique, CodeSearch, Tricorder, and
language-specific Google style guides.e Rosie. We discuss the pros and cons
f The project name was inspired by Rosie the ro-
Google has written a code-review tool bot maid from the TV series “The Jetsons.” of this model here.
called Critique that allows the reviewer
to view the evolution of the code and Figure 6. Release branching model.
comment on any line of the change.
It encourages further revisions and a
conversation leading to a final “Looks Trunk/Mainline
Good To Me” from the reviewer, indi-
cating the review is complete. Cherry-pick
Google’s static analysis system (Tri-
corder10) and presubmit infrastructure
Release branch
also provide data on code quality, test
coverage, and test results automatical-
ly in the Google code-review tool. These
computationally intensive checks are Figure 7. Rosie commits per month.
triggered periodically, as well as when
a code change is sent for review. Tri-
corder also provides suggested fixes
with one-click code editing for many 15,000
errors. These systems provide impor-
tant data to increase the effectiveness
of code reviews and keep the Google 10,000
codebase healthy.
A team of Google developers will
occasionally undertake a set of wide-
5,000
reaching code-cleanup changes to fur-
ther maintain the health of the code-
base. The developers who perform
these changes commonly separate
Jan. 2011 Jan. 2012 Jan. 2013 Jan. 2014 Jan. 2015
e https://github.com/google/styleguide
JULY 2016 | VOL. 59 | NO. 7 | COMMUNICATIONS OF THE ACM 83

--- Page 7 ---
contributed articles
Analysis sioned in the same repository, there binary problem is avoided through use
This section outlines and expands is only ever one version of the truth, of static linking.
upon both the advantages of a mono- and no concern about independent The ability to make atomic changes
lithic codebase and the costs related to versioning of dependencies. is also a very powerful feature of the
maintaining such a model at scale. Most notably, the model allows monolithic model. A developer can
Advantages. Supporting the ultra- Google to avoid the “diamond depen- make a major change touching hun-
large-scale of Google’s codebase while dency” problem (see Figure 8) that oc- dreds or thousands of files across the
maintaining good performance for curs when A depends on B and C, both repository in a single consistent op-
tens of thousands of users is a chal- B and C depend on D, but B requires eration. For instance, a developer can
lenge, but Google has embraced the version D.1 and C requires version D.2. rename a class or function in a single
monolithic model due to its compel- In most cases it is now impossible to commit and yet not break any builds
ling advantages. build A. For the base library D, it can or tests.
Most important, it supports: become very difficult to release a new The availability of all source code
˲ Unified versioning, one source of version without causing breakage, in a single repository, or at least on a
truth; since all its callers must be updated centralized server, makes it easier for
˲ Extensive code sharing and reuse; at the same time. Updating is difficult the maintainers of core libraries to per-
˲ Simplified dependency manage- when the library callers are hosted in form testing and performance bench-
ment; different repositories. marking for high-impact changes be-
˲ Atomic changes; In the open source world, depen- fore they are committed. This approach
˲ Large-scale refactoring; dencies are commonly broken by li- is useful for exploring and measuring
˲ Collaboration across teams; brary updates, and finding library ver- the value of highly disruptive changes.
˲ Flexible team boundaries and code sions that all work together can be a One concrete example is an experiment
ownership; and challenge. Updating the versions of to evaluate the feasibility of converting
˲ Code visibility and clear tree dependencies can be painful for devel- Google data centers to support non-x86
structure providing implicit team opers, and delays in updating create machine architectures.
namespacing. technical debt that can become very With the monolithic structure of
A single repository provides unified expensive. In contrast, with a mono- the Google repository, a developer
versioning and a single source of truth. lithic source tree it makes sense, and never has to decide where the reposi-
There is no confusion about which re- is easier, for the person updating a li- tory boundaries lie. Engineers never
pository hosts the authoritative version brary to update all affected dependen- need to “fork” the development of
of a file. If one team wants to depend cies at the same time. The technical a shared library or merge across re-
on another team’s code, it can depend debt incurred by dependent systems is positories to update copied versions
on it directly. The Google codebase in- paid down immediately as changes are of code. Team boundaries are fluid.
cludes a wealth of useful libraries, and made. Changes to base libraries are in- When project ownership changes or
the monolithic repository leads to ex- stantly propagated through the depen- plans are made to consolidate sys-
tensive code sharing and reuse. dency chain into the final products that tems, all code is already in the same
The Google build system5 makes it rely on the libraries, without requiring repository. This environment makes
easy to include code across directo- a separate sync or migration step. it easy to do gradual refactoring and
ries, simplifying dependency manage- Note the diamond-dependency reorganization of the codebase. The
ment. Changes to the dependencies problem can exist at the source/API change to move a project and up-
of a project trigger a rebuild of the level, as described here, as well as date all dependencies can be applied
dependent code. Since all code is ver- between binaries.12 At Google, the atomically to the repository, and the
development history of the affected
Figure 8. Diamond dependency problem. code remains intact and available.
Another attribute of a monolithic
repository is the layout of the code-
base is easily understood, as it is orga-
nized in a single tree. Each team has
A A a directory structure within the main
tree that effectively serves as a proj-
ect’s own namespace. Each source file
can be uniquely identified by a single
B C B C
string—a file path that optionally in-
cludes a revision number. Browsing
the codebase, it is easy to understand
how any source file fits into the big pic-
D D.1 D.2
ture of the repository.
The Google codebase is constantly
evolving. More complex codebase
modernization efforts (such as updat-
84 COMMUNICATIONS OF THE ACM | JULY 2016 | VOL. 59 | NO. 7

--- Page 8 ---
contributed articles
ing it to C++11 or rolling out perfor- (often used in conjunction with Rosie)
mance optimizations9) are often man- make use of the monolithic view of
aged centrally by dedicated codebase Google’s source to perform high-level
maintainers. Such efforts can touch transformations of source code. The
half a million variable declarations or An important aspect monolithic codebase captures all de-
function-call sites spread across hun- pendency information. Old APIs can
of Google culture
dreds of thousands of files of source be removed with confidence, because
code. Because all projects are central- that encourages it can be proven that all callers have
ly stored, teams of specialists can do been migrated to new APIs. A single
this work for the entire company, rath- code quality is common repository vastly simplifies
er than require many individuals to these tools by ensuring atomicity of
the expectation
develop their own tools, techniques, changes and a single global view of
or expertise. that all code is the entire repository at any given time.
As an example of how these ben- Costs and trade-offs. While impor-
reviewed before
efits play out, consider Google’s Com- tant to note a monolithic codebase in
piler team, which ensures developers being committed no way implies monolithic software de-
at Google employ the most up-to-date sign, working with this model involves
to the repository.
toolchains and benefit from the lat- some downsides, as well as trade-offs,
est improvements in generated code that must be considered.
and “debuggability.” The monolithic These costs and trade-offs fall into
repository provides the team with three categories:
full visibility of how various languag- ˲ Tooling investments for both de-
es are used at Google and allows them velopment and execution;
to do codebase-wide cleanups to pre- ˲ Codebase complexity, including
vent changes from breaking builds or unnecessary dependencies and diffi-
creating issues for developers. This culties with code discovery; and
greatly simplifies compiler validation, ˲ Effort invested in code health.
thus reducing compiler release cycles In many ways the monolithic repos-
and making it possible for Google to itory yields simpler tooling since there
safely do regular compiler releases is only one system of reference for
(typically more than 20 per year for the tools working with source. However, it
C++ compilers). is also necessary that tooling scale to
Using the data generated by perfor- the size of the repository. For instance,
mance and regression tests run on Google has written a custom plug-in for
nightly builds of the entire Google the Eclipse integrated development
codebase, the Compiler team tunes de- environment (IDE) to make work-
fault compiler settings to be optimal. ing with a massive codebase possible
For example, due to this centralized from the IDE. Google’s code-indexing
effort, Google’s Java developers all saw system supports static analysis, cross-
their garbage collection (GC) CPU con- referencing in the code-browsing tool,
sumption decrease by more than 50% and rich IDE functionality for Emacs,
and their GC pause time decrease by Vim, and other development environ-
10%–40% from 2014 to 2015. In addi- ments. These tools require ongoing in-
tion, when software errors are discov- vestment to manage the ever-increas-
ered, it is often possible for the team ing scale of the Google codebase.
to add new warnings to prevent reoc- Beyond the investment in build-
currence. In conjunction with this ing and maintaining scalable tooling,
change, they scan the entire reposi- Google must also cover the cost of run-
tory to find and fix other instances of ning these systems, some of which are
the software issue being addressed, very computationally intensive. Much
before turning to new compiler er- of Google’s internal suite of devel-
rors. Having the compiler-reject pat- oper tools, including the automated
terns that proved problematic in the test infrastructure and highly scalable
past is a significant boost to Google’s build infrastructure, are critical for
overall code health. supporting the size of the monolithic
Storing all source code in a common codebase. It is thus necessary to make
version-control repository allows code- trade-offs concerning how frequently
base maintainers to efficiently ana- to run this tooling to balance the cost
lyze and change Google’s source code. of execution vs. the benefit of the data
Tools like Refaster11 and ClangMR15 provided to developers.
JULY 2016 | VOL. 59 | NO. 7 | COMMUNICATIONS OF THE ACM 85

--- Page 9 ---
contributed articles
The monolithic model makes it Dependency-refactoring and clean-
easier to understand the structure of up tools are helpful, but, ideally, code
the codebase, as there is no crossing of owners should be able to prevent un-
repository boundaries between depen- wanted dependencies from being cre-
dencies. However, as the scale increas- A developer can ated in the first place. In 2011, Google
es, code discovery can become more started relying on the concept of
make a major
difficult, as standard tools like grep API visibility, setting the default
bog down. Developers must be able change touching visibility of new APIs to “private.”
to explore the codebase, find relevant This forces developers to explicitly
libraries, and see how to use them hundreds or mark APIs as appropriate for use by
and who wrote them. Library authors other teams. A lesson learned from
thousands of
often need to see how their APIs are Google’s experience with a large
being used. This requires a signifi- files across the monolithic repository is such mech-
cant investment in code search and anisms should be put in place as soon
repository in a
browsing tools. However, Google has as possible to encourage more hygienic
found this investment highly reward- single consistent dependency structures.
ing, improving the productivity of all The fact that most Google code is
operation.
developers, as described in more detail available to all Google developers has
by Sadowski et al.9 led to a culture where some teams ex-
Access to the whole codebase en- pect other developers to read their
courages extensive code sharing and code rather than providing them with
reuse. Some would argue this model, separate user documentation. There
which relies on the extreme scalabil- are pros and cons to this approach. No
ity of the Google build system, makes effort goes toward writing or keeping
it too easy to add dependencies and documentation up to date, but devel-
reduces the incentive for software de- opers sometimes read more than the
velopers to produce stable and well- API code and end up relying on under-
thought-out APIs. lying implementation details. This be-
Due to the ease of creating dependen- havior can create a maintenance bur-
cies, it is common for teams to not think den for teams that then have trouble
about their dependency graph, making deprecating features they never meant
code cleanup more error-prone. Un- to expose to users.
necessary dependencies can increase This model also requires teams to
project exposure to downstream build collaborate with one another when us-
breakages, lead to binary size bloating, ing open source code. An area of the
and create additional work in building repository is reserved for storing open
and testing. In addition, lost productiv- source code (developed at Google or
ity ensues when abandoned projects externally). To prevent dependency
that remain in the repository continue conflicts, as outlined earlier, it is im-
to be updated and maintained. portant that only one version of an
Several efforts at Google have open source project be available at
sought to rein in unnecessary depen- any given time. Teams that use open
dencies. Tooling exists to help identify source software are expected to occa-
and remove unused dependencies, or sionally spend time upgrading their
dependencies linked into the prod- codebase to work with newer versions
uct binary for historical or accidental of open source libraries when library
reasons, that are not needed. Tooling upgrades are performed.
also exists to identify underutilized Google invests significant effort in
dependencies, or dependencies on maintaining code health to address
large libraries that are mostly unneed- some issues related to codebase com-
ed, as candidates for refactoring.7 One plexity and dependency manage-
such tool, Clipper, relies on a custom ment. For instance, special tooling
Java compiler to generate an accurate automatically detects and removes
cross-reference index. It then uses the dead code, splits large refactorings
index to construct a reachability graph and automatically assigns code re-
and determine what classes are never views (as through Rosie), and marks
used. Clipper is useful in guiding de- APIs as deprecated. Human effort is
pendency-refactoring efforts by finding required to run these tools and man-
targets that are relatively easy to remove age the corresponding large-scale
or break up. code changes. A cost is also incurred
86 COMMUNICATIONS OF THE ACM | JULY 2016 | VOL. 59 | NO. 7

--- Page 10 ---
contributed articles
by teams that need to review an ongo- repository. This effort is in collabora- Tech Leads of CitC; Hyrum Wright,
ing stream of simple refactorings re- tion with the open source Mercurial Google’s large-scale refactoring guru;
sulting from codebase-wide clean-ups community, including contributors and Chris Colohan, Caitlin Sadowski,
and centralized modernization efforts. from other companies that value the Morgan Ames, Rob Siemborski, and
monolithic source model. the Piper and CitC development and
Alternatives support teams for their insightful re-
As the popularity and use of distrib- Conclusion view comments.
uted version control systems (DVCSs) Google chose the monolithic-source-
like Git have grown, Google has con- management strategy in 1999 when
References
sidered whether to move from Piper the existing Google codebase was 1. Bloch, D. Still All on One Server: Perforce at Scale.
to Git as its primary version-control migrated from CVS to Perforce. Early Google White Paper, 2011; http://info.perforce.
com/rs/perforce/images/GoogleWhitePaper-
system. A team at Google is focused Google engineers maintained that a StillAllonOneServer-PerforceatScale.pdf
on supporting Git, which is used by single repository was strictly better 2. Chang, F., Dean, J., Ghemawat, S., Hsieh, W.C.,
Wallach, D.A., Burrows, M., Chandra, T., Fikes, A., and
Google’s Android and Chrome teams than splitting up the codebase, though Gruber, R.E. Bigtable: A distributed storage system
outside the main Google repository. at the time they did not anticipate the for structured data. ACM Transactions on Computer
Systems 26, 2 (June 2008).
The use of Git is important for these future scale of the codebase and all 3. Corbett, J.C., Dean, J., Epstein, M., Fikes, A., Frost,
teams due to external partner and open the supporting tooling that would be C., Furman, J., Ghemawat, S., Gubarev, A., Heiser,
C., Hochschild, P. et al. Spanner: Google’s globally
source collaborations. built to make the scaling feasible. distributed database. ACM Transactions on Computer
Systems 31, 3 (Aug. 2013).
The Git community strongly sug- Over the years, as the investment re-
4. Gabriel, R.P., Northrop, L., Schmidt, D.C., and Sullivan,
gests and prefers developers have quired to continue scaling the central- K. Ultra-large-scale systems. In Companion to the
21st ACM SIGPLAN Symposium on Object-Oriented
more and smaller repositories. A Git- ized repository grew, Google leader-
Programming Systems, Languages, and Applications
clone operation requires copying all ship occasionally considered whether (Portland, OR, Oct. 22–26). ACM Press, New York,
2006, 632–634.
content to one’s local machine, a pro- it would make sense to move from the
5. Kemper, C. Build in the Cloud: How the Build System
cedure incompatible with a large re- monolithic model. Despite the effort works. Google Engineering Tools blog post, 2011;
http://google-engtools.blogspot.com/2011/08/build-
pository. To move to Git-based source required, Google repeatedly chose to in-cloud-how-build-system-works.html
hosting, it would be necessary to split stick with the central repository due to 6. Lamport, L. Paxos made simple. ACM Sigact News 32,
4 (Nov. 2001), 18–25.
Google’s repository into thousands of its advantages. 7. Morgenthaler, J.D., Gridnev, M., Sauciuc, R., and
separate repositories to achieve reason- The monolithic model of source Bhansali, S. Searching for build debt: Experiences
managing technical debt at Google. In Proceedings
able performance. Such reorganization code management is not for everyone. of the Third International Workshop on Managing
would necessitate cultural and work- It is best suited to organizations like Technical Debt (Zürich, Switzerland, June 2–9). IEEE
Press Piscataway, NJ, 2012, 1–6.
flow changes for Google’s developers. Google, with an open and collabora- 8. Ren, G., Tune, E., Moseley, T., Shi, Y., Rus, S., and
As a comparison, Google’s Git-hosted tive culture. It would not work well Hundt, R. Google-wide profiling: A continuous profiling
infrastructure for data centers. IEEE Micro 30, 4
Android codebase is divided into more for organizations where large parts (2010), 65–79.
9. Sadowski, C., Stolee, K., and Elbaum, S. How
than 800 separate repositories. of the codebase are private or hidden
developers search for code: A case study. In
Given the value gained from the ex- between groups. Proceedings of the 10th Joint Meeting on Foundations
of Software Engineering (Bergamo, Italy, Aug. 30–
isting tools Google has built and the At Google, we have found, with some
Sept. 4). ACM Press, New York, 2015, 191–201.
many advantages of the monolithic investment, the monolithic model of 10. Sadowski, C., van Gogh, J., Jaspan, C., Soederberg, E.,
and Winter, C. Tricorder: Building a program analysis
codebase structure, it is clear that mov- source management can scale success-
ecosystem. In Proceedings of the 37th International
ing to more and smaller repositories fully to a codebase with more than one Conference on Software Engineering, Vol. 1 (Firenze,
Italy, May 16–24). IEEE Press Piscataway, NJ, 2015,
would not make sense for Google’s billion files, 35 million commits, and 598–608.
main repository. The alternative of thousands of users around the globe. As 11. Wasserman, L. Scalable, example-based refactorings
with Refaster. In Proceedings of the 2013 ACM
moving to Git or any other DVCS that the scale and complexity of projects both Workshop on Refactoring Tools (Indianapolis, IN, Oct.
would require repository splitting is inside and outside Google continue to 26–31). ACM Press, New York, 2013, 25–28.
12. Wikipedia. Dependency hell. Accessed Jan.
not compelling for Google. grow, we hope the analysis and workflow 20, 2015; http://en.wikipedia.org/w/index.
Current investment by the Google described in this article can benefit oth- php?title=Dependency_hell&oldid=634636715
13. Wikipedia. Filesystem in userspace.
source team focuses primarily on the ers weighing decisions on the long-term Accessed June, 4, 2015; http://en.wikipedia.
ongoing reliability, scalability, and structure for their codebases. org/w/index.php?title=Filesystem_in_
Userspace&oldid=664776514
security of the in-house source sys- 14. Wikipedia. Linux kernel. Accessed Jan. 20, 2015;
tems. The team is also pursuing an Acknowledgments http://en.wikipedia.org/w/index.php?title=Linux_
kernel&oldid=643170399
experimental effort with Mercurial,g We would like to recognize all current 15. Wright, H.K., Jasper, D., Klimek, M., Carruth, C., and
Wan, Z. Large-scale automated refactoring using
an open source DVCS similar to Git. and former members of the Google
ClangMR. In Proceedings of the IEEE International
The goal is to add scalability fea- Developer Infrastructure teams for Conference on Software Maintenance (Eindhoven,
The Netherlands, Sept. 22–28). IEEE Press, 2013,
tures to the Mercurial client so it can their dedication in building and
548–551.
efficiently support a codebase the maintaining the systems referenced
size of Google’s. This would provide in this article, as well as the many
Rachel Potvin (rpotvin@google.com) is an engineering
Google’s developers with an alterna- people who helped in reviewing the manager at Google, Mountain View, CA.
tive of using popular DVCS-style work- article; in particular: Jon Perkins and
Josh Levenberg (joshl@google.com) is a software
flows in conjunction with the central Ingo Walther, the current Tech Leads engineer at Google, Mountain View, CA.
of Piper; Kyle Lippincott and Crutcher
g http://mercurial.selenic.com/ Dunnavant, the current and former Copyright held by the authors
JULY 2016 | VOL. 59 | NO. 7 | COMMUNICATIONS OF THE ACM 87