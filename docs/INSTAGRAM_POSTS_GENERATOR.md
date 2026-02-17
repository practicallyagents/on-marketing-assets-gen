# Instagram posts generator

The idea for instagram posts generator is simple - it's a tool for marketing people to generate assets that the team could use on Instagem.

The system is split into following components:

- Ideation agent
- Assets generator

## Ideation Agent

Given a markdown document with marketing ideas, let's call it "Mood board" as an Input the system should

1. generate 3 ideas for instagram posts considering
   a. what products could we push
   b. what imagery to use, i.e. real world shots, marathon finish line shot, product shot, etc.
2. create a copy for the post
   a. headline
   b. text for post description

The system shoud output a JSON file containing each idea that Assets generator could pick up and use to generate assets.

## Assets Generator agent

This agent takes JSON from Ideation agent, iterates through contained ideas and generates 3 versions of each idea.
