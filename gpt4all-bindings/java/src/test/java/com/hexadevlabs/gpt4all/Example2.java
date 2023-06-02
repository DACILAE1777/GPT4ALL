package com.hexadevlabs.gpt4all;

import java.nio.file.Path;

/**
 * Generation with MPT model
 */
public class Example2 {
    public static void main(String[] args) {

        String prompt = "### Human:\nWhat is the meaning of life\n### Assistant:";

        // Optionally in case extra search path are necessary.
        //LLModel.LIBRARY_SEARCH_PATH = "C:\\Users\\felix\\gpt4all\\lib\\";

        try (MPTModel mptModel = new MPTModel(Path.of("C:\\Users\\felix\\AppData\\Local\\nomic.ai\\GPT4All\\ggml-mpt-7b-instruct.bin"))) {

            LLModel.GenerationConfig config =
                    LLModel.config()
                    .withNPredict(4096)
                    .withRepeatLastN(64)
                    .build();

            mptModel.generate(prompt, config, true);

        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

}
